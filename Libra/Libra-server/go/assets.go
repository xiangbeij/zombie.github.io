package main

import (
	"crypto/sha1"
	"crypto/tls"
	"crypto/x509"
	"database/sql"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"log"
	"math"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

// ─── Asset Models ─────────────────────────────────────────────────────────────

type Asset struct {
	ID                 int64   `json:"id"`
	AssetType          string  `json:"asset_type"`   // domain | ip | cert
	Value              string  `json:"value"`        // hostname / IP / cert SHA1
	Port               int     `json:"port"`         // 80 | 443 | 其他
	Scheme             string  `json:"scheme"`       // http | https
	Title              string  `json:"title"`
	ServerFingerprint  string  `json:"server_fingerprint"`
	StatusCode         int     `json:"status_code"`
	ContentHash        string  `json:"content_hash"`
	Tags               string  `json:"tags"`
	Status             string  `json:"status"` // active | inactive | unknown
	FirstSeen          string  `json:"first_seen"`
	LastSeen           string  `json:"last_seen"`
	Note               string  `json:"note"`
	CertID             int64   `json:"cert_id,omitempty"`
	IPRangeID          int64   `json:"ip_range_id,omitempty"`
}

type IPRange struct {
	ID          int64  `json:"id"`
	CIDR        string `json:"cidr"`
	Description string `json:"description"`
	Tags        string `json:"tags"`
	CreatedAt   string `json:"created_at"`
}

type CertAsset struct {
	ID           int64   `json:"id"`
	CertSHA1     string  `json:"cert_sha1"`
	CertSubject  string  `json:"cert_subject"`
	CertIssuer   string  `json:"cert_issuer"`
	CertNotBefore string `json:"cert_not_before"`
	CertNotAfter  string `json:"cert_not_after"`
	SANCount     int     `json:"san_count"`
	Domains      []string `json:"domains"`
	ImportedAt   string  `json:"imported_at"`
}

type AssetSnapshot struct {
	ID           int64   `json:"id"`
	AssetID      int64   `json:"asset_id"`
	URL          string  `json:"url"`
	Title        string  `json:"title"`
	Keywords     string  `json:"keywords"`
	Description  string  `json:"description"`
	ContentHash  string  `json:"content_hash"`
	DiffRatio    float64 `json:"diff_ratio"`
	ScannedAt    string  `json:"scanned_at"`
}

type TamperAlert struct {
	ID           int64   `json:"id"`
	AssetID      int64   `json:"asset_id"`
	SnapshotID   int64   `json:"snapshot_id"`
	AlertType    string  `json:"alert_type"`
	AlertDetail  string  `json:"alert_detail"` // JSON string
	Confirmed    int     `json:"confirmed"`    // 0=未确�?1=误报 2=真实篡改
	ConfirmedAt  string  `json:"confirmed_at"`
	ConfirmedBy  string  `json:"confirmed_by"`
	CreatedAt    string  `json:"created_at"`
	AssetValue   string  `json:"asset_value,omitempty"` // join field
	AssetURL     string  `json:"asset_url,omitempty"`
}

// Asset scan task (async)
type assetScanJob struct {
	Target   string
	JobType  string // "ip_range" | "cert"
	RangeID  int64
}

// ─── Asset Handlers ──────────────────────────────────────────────────────────

func handleAssets(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	path := strings.TrimPrefix(r.URL.Path, "/api/assets")

	// GET /api/assets - list assets
	if r.Method == http.MethodGet && path == "" {
		listAssets(w, r)
		return
	}

	// POST /api/assets - create / import asset manually
	if r.Method == http.MethodPost && path == "" {
		createAsset(w, r)
		return
	}

	// GET /api/assets/stats
	if r.Method == http.MethodGet && path == "/stats" {
		getAssetStats(w, r)
		return
	}

	// POST /api/assets/scan/ip
	if r.Method == http.MethodPost && path == "/scan/ip" {
		scanIPRange(w, r)
		return
	}

	// POST /api/assets/scan/cert
	if r.Method == http.MethodPost && path == "/scan/cert" {
		importCert(w, r)
		return
	}

	// ── IPRange CRUD ─────────────────────────────────────────────────────────

	// GET/POST /api/assets/ip-ranges
	if r.Method == http.MethodGet && path == "/ip-ranges" {
		listIPRanges(w, r)
		return
	}
	if r.Method == http.MethodPost && path == "/ip-ranges" {
		addIPRange(w, r)
		return
	}

	// DELETE /api/assets/ip-ranges/:id
	if r.Method == http.MethodDelete && strings.HasPrefix(path, "/ip-ranges/") {
		rangeID := strings.TrimPrefix(path, "/ip-ranges/")
		deleteIPRange(w, r, rangeID)
		return
	}

	// ── Snapshots ─────────────────────────────────────────────────────────────

	// POST /api/assets/snapshot/:id
	if r.Method == http.MethodPost && strings.HasPrefix(path, "/snapshot/") {
		assetID := strings.TrimPrefix(path, "/snapshot/")
		takeSnapshot(w, r, assetID)
		return
	}

	// GET /api/assets/snapshots/:asset_id
	if r.Method == http.MethodGet && strings.HasPrefix(path, "/snapshots/") {
		assetID := strings.TrimPrefix(path, "/snapshots/")
		getSnapshots(w, r, assetID)
		return
	}

	// ── Tamper Alerts ──────────────────────────────────────────────────────────

	// GET /api/assets/alerts
	if r.Method == http.MethodGet && path == "/alerts" {
		getTamperAlerts(w, r)
		return
	}

	// PUT /api/assets/alerts/:id/confirm
	if r.Method == http.MethodPut && strings.HasPrefix(path, "/alerts/") && strings.HasSuffix(path, "/confirm") {
		alertID := strings.Trim(strings.TrimPrefix(path, "/alerts/"), "/confirm")
		confirmAlert(w, r, alertID)
		return
	}

	// DELETE /api/assets/alerts/:id
	if r.Method == http.MethodDelete && strings.HasPrefix(path, "/alerts/") {
		alertID := strings.TrimPrefix(path, "/alerts/")
		deleteAlert(w, r, alertID)
		return
	}

	respErr(w, 404, "not found")
}

// ─── List Assets ───────────────────────────────────────────────────────────────

func listAssets(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	page := atoi(q.Get("page"), 1)
	pageSize := atoi(q.Get("page_size"), 50)
	search := q.Get("search")
	assetType := q.Get("type")
	status := q.Get("status")
	tags := q.Get("tags")
	offset := (page - 1) * pageSize

	dbPath := filepath.Join(*baseDir, "Libra.db")
	log.Printf("[assets] listAssets: dbPath=%s", dbPath)
	db, err := openDB(dbPath)
	if err != nil {
		log.Printf("[assets] openDB error: %v", err)
		respErr(w, 500, "db error: "+err.Error())
		return
	}
	defer db.Close()

	where := "1=1"
	args := []interface{}{}
	if search != "" {
		where += " AND (value LIKE ? OR title LIKE ? OR tags LIKE ?)"
		like := "%" + search + "%"
		args = append(args, like, like, like)
	}
	if assetType != "" {
		where += " AND asset_type = ?"
		args = append(args, assetType)
	}
	if status != "" {
		where += " AND status = ?"
		args = append(args, status)
	}
	if tags != "" {
		where += " AND tags LIKE ?"
		args = append(args, "%"+tags+"%")
	}

	var total int
	countSQL := fmt.Sprintf("SELECT COUNT(*) FROM assets WHERE %s", where)
	log.Printf("[assets] COUNT sql=%s args=%v", countSQL, args)
	if err := db.QueryRow(countSQL, args...).Scan(&total); err != nil {
		log.Printf("[assets] COUNT query error: %v", err)
		respErr(w, 500, "count error: "+err.Error())
		return
	}

	sqlStr := fmt.Sprintf(`SELECT id, asset_type, value, port, scheme, title, server_fingerprint,
		status_code, content_hash, tags, status, first_seen, last_seen, note, cert_id, ip_range_id
		FROM assets WHERE %s ORDER BY last_seen DESC LIMIT ? OFFSET ?`, where)
	args = append(args, pageSize, offset)

	rows, err := db.Query(sqlStr, args...)
	if err != nil {
		respErr(w, 500, "query error")
		return
	}
	defer rows.Close()

	assets := []Asset{}
	for rows.Next() {
		var a Asset
		err := rows.Scan(&a.ID, &a.AssetType, &a.Value, &a.Port, &a.Scheme,
			&a.Title, &a.ServerFingerprint, &a.StatusCode, &a.ContentHash,
			&a.Tags, &a.Status, &a.FirstSeen, &a.LastSeen, &a.Note, &a.CertID, &a.IPRangeID)
		if err == nil {
			assets = append(assets, a)
		}
	}

	respJSON(w, map[string]interface{}{
		"assets":     assets,
		"total":      total,
		"page":       page,
		"page_size":  pageSize,
		"total_pages": int(math.Ceil(float64(total) / float64(pageSize))),
	})
}

// ─── Create Asset Manually ────────────────────────────────────────────────────

func createAsset(w http.ResponseWriter, r *http.Request) {
	var req struct {
		AssetType string `json:"asset_type"`
		Value     string `json:"value"`
		Port      int    `json:"port"`
		Scheme    string `json:"scheme"`
		Tags      string `json:"tags"`
		Note      string `json:"note"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}
	if req.AssetType == "" || req.Value == "" {
		respErr(w, 400, "asset_type and value required")
		return
	}
	if req.Scheme == "" {
		req.Scheme = "https"
	}
	if req.Port == 0 {
		if req.Scheme == "http" {
			req.Port = 80
		} else {
			req.Port = 443
		}
	}

	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	now := timeNowStr()
	_, err = db.Exec(`INSERT OR REPLACE INTO assets
		(asset_type, value, port, scheme, tags, note, status, first_seen, last_seen)
		VALUES (?, ?, ?, ?, ?, ?, 'unknown', ?, ?)`,
		req.AssetType, req.Value, req.Port, req.Scheme, req.Tags, req.Note, now, now)
	if err != nil {
		respErr(w, 500, "insert error: "+err.Error())
		return
	}

	respJSON(w, map[string]string{"status": "created"})
}

// ─── Asset Stats ──────────────────────────────────────────────────────────────

func getAssetStats(w http.ResponseWriter, r *http.Request) {
	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	var totalAssets, domainCount, ipCount, certCount int
	var activeCount, inactiveCount, unknownCount int

	db.QueryRow("SELECT COUNT(*) FROM assets").Scan(&totalAssets)
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE asset_type='domain'").Scan(&domainCount)
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE asset_type='ip'").Scan(&ipCount)
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE asset_type='cert'").Scan(&certCount)
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE status='active'").Scan(&activeCount)
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE status='inactive'").Scan(&inactiveCount)
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE status='unknown'").Scan(&unknownCount)

	var totalSnapshots, tamperAlerts int
	db.QueryRow("SELECT COUNT(*) FROM asset_snapshots").Scan(&totalSnapshots)
	db.QueryRow("SELECT COUNT(*) FROM tamper_alerts WHERE confirmed=0").Scan(&tamperAlerts)

	var ipRangeCount int
	db.QueryRow("SELECT COUNT(*) FROM ip_ranges").Scan(&ipRangeCount)

	var certImportCount int
	db.QueryRow("SELECT COUNT(*) FROM cert_assets").Scan(&certImportCount)

	respJSON(w, map[string]interface{}{
		"total_assets":    totalAssets,
		"by_type":         map[string]int{"domain": domainCount, "ip": ipCount, "cert": certCount},
		"by_status":       map[string]int{"active": activeCount, "inactive": inactiveCount, "unknown": unknownCount},
		"total_snapshots": totalSnapshots,
		"pending_alerts":  tamperAlerts,
		"ip_ranges":       ipRangeCount,
		"cert_imports":     certImportCount,
	})
}

// ─── IP Range Management ──────────────────────────────────────────────────────

func listIPRanges(w http.ResponseWriter, r *http.Request) {
	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	rows, err := db.Query("SELECT id, cidr, description, tags, created_at FROM ip_ranges ORDER BY created_at DESC")
	if err != nil {
		respErr(w, 500, "query error")
		return
	}
	defer rows.Close()

	var ranges []IPRange
	for rows.Next() {
		var r IPRange
		rows.Scan(&r.ID, &r.CIDR, &r.Description, &r.Tags, &r.CreatedAt)
		ranges = append(ranges, r)
	}
	respJSON(w, map[string]interface{}{"ip_ranges": ranges})
}

func addIPRange(w http.ResponseWriter, r *http.Request) {
	var req struct {
		CIDR        string `json:"cidr"`
		Description string `json:"description"`
		Tags        string `json:"tags"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}
	req.CIDR = strings.TrimSpace(req.CIDR)
	if req.CIDR == "" {
		respErr(w, 400, "cidr required")
		return
	}
	// Validate CIDR
	if _, _, err := net.ParseCIDR(req.CIDR); err != nil {
		respErr(w, 400, "invalid CIDR: "+err.Error())
		return
	}

	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	now := timeNowStr()
	res, err := db.Exec(`INSERT INTO ip_ranges (cidr, description, tags, created_at) VALUES (?, ?, ?, ?)`,
		req.CIDR, req.Description, req.Tags, now)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			respErr(w, 409, "CIDR already exists")
			return
		}
		respErr(w, 500, "insert error: "+err.Error())
		return
	}
	id, _ := res.LastInsertId()
	respJSON(w, map[string]interface{}{"id": id, "status": "created"})
}

func deleteIPRange(w http.ResponseWriter, r *http.Request, idStr string) {
	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	_, err = db.Exec("DELETE FROM ip_ranges WHERE id = ?", idStr)
	if err != nil {
		respErr(w, 500, "delete error")
		return
	}
	respJSON(w, map[string]string{"status": "deleted"})
}

// ─── IP Range Scan ────────────────────────────────────────────────────────────

// assetScanQueue for async IP range scans
var assetScanQueue = make(chan assetScanJob, 100)
var assetScanWg sync.WaitGroup

func init() {
	// Start 3 concurrent asset scanners
	for i := 0; i < 3; i++ {
		go assetScannerWorker(i)
	}
}

func scanIPRange(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	var req struct {
		RangeID int64 `json:"range_id"` // specific range, or...
		CIDR    string `json:"cidr"`     // or direct CIDR
		Ports   string `json:"ports"`    // e.g. "80,443"
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}

	cidr := req.CIDR
	if cidr == "" && req.RangeID > 0 {
		dbPath := filepath.Join(*baseDir, "Libra.db")
		db, err := openDB(dbPath)
		if err != nil {
			respErr(w, 500, "db error")
			return
		}
		var cidrStr string
		db.QueryRow("SELECT cidr FROM ip_ranges WHERE id = ?", req.RangeID).Scan(&cidrStr)
		db.Close()
		cidr = cidrStr
	}

	if cidr == "" {
		respErr(w, 400, "cidr or range_id required")
		return
	}

	if _, _, err := net.ParseCIDR(cidr); err != nil {
		respErr(w, 400, "invalid CIDR")
		return
	}

	ports := req.Ports
	if ports == "" {
		ports = "80,443"
	}

	// Queue scan job
	job := assetScanJob{Target: cidr, JobType: "ip_range", RangeID: req.RangeID}
	select {
	case assetScanQueue <- job:
		// ok
	default:
		respErr(w, 429, "scan queue full, try again later")
		return
	}

	respJSON(w, map[string]interface{}{
		"status":   "scanning",
		"cidr":     cidr,
		"ports":    ports,
		"message":  "IP range scan started in background",
	})
}

func assetScannerWorker(id int) {
	for job := range assetScanQueue {
		log.Printf("[asset-scan-%d] starting %s scan: %s", id, job.JobType, job.Target)
		switch job.JobType {
		case "ip_range":
			execIPRangeScan(job.Target, job.RangeID)
		case "cert":
			go execCertImport(job.Target)
		}
	}
}

func execIPRangeScan(cidr string, rangeID int64) {
	assetScanWg.Add(1)
	defer assetScanWg.Done()

	dbPath := filepath.Join(*baseDir, "Libra.db")

	// Use masscan if available, otherwise fall back to native Go scan
	masscanBIN := findMasscan()
	ports := "80,443"

	var foundHosts []string
	if masscanBIN != "" {
		foundHosts = runMasscan(cidr, ports, masscanBIN)
	} else {
		foundHosts = goSyncScan(cidr)
	}

	if len(foundHosts) == 0 {
		log.Printf("[asset-scan] no hosts found in %s", cidr)
		return
	}

	// Fingerprint each host with httpx or native
	fingerprinted := fingerprintHosts(foundHosts, ports)

	db, err := openDB(dbPath)
	if err != nil {
		log.Printf("[asset-scan] db error: %v", err)
		return
	}
	defer db.Close()

	now := timeNowStr()
	for _, h := range fingerprinted {
		scheme := "http"
		if h.Port == 443 || strings.Contains(h.Title, "HTTPS") {
			scheme = "https"
		}
		var title, server string
		var statusCode int
		title = h.Title
		server = h.Server
		statusCode = h.StatusCode

		status := "active"
		if statusCode == 0 {
			status = "unknown"
		} else if statusCode >= 400 {
			status = "inactive"
		}

		_, err = db.Exec(`INSERT OR REPLACE INTO assets
			(asset_type, value, port, scheme, title, server_fingerprint, status_code, status,
			 tags, first_seen, last_seen, ip_range_id)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			"ip", h.IP, h.Port, scheme, title, server, statusCode, status,
			"", now, now, rangeID)
		if err != nil {
			log.Printf("[asset-scan] insert error for %s: %v", h.IP, err)
		}
	}
	log.Printf("[asset-scan] completed %s: %d hosts found, %d fingerprinted",
		cidr, len(foundHosts), len(fingerprinted))
}

// ─── IP Scan Utilities ─────────────────────────────────────────────────────────

func findMasscan() string {
	for _, bin := range []string{"/usr/bin/masscan", "/usr/local/bin/masscan", "masscan"} {
		if exec.Command(bin, "--version").Run() == nil {
			return bin
		}
	}
	return ""
}

func runMasscan(cidr, ports, masscanBIN string) []string {
	tmpFile := filepath.Join(os.TempDir(), "masscan_"+uuid.New().String()[:8]+".json")
	defer os.Remove(tmpFile)

	cmd := exec.Command(masscanBIN, cidr, "-p", ports,
		"--rate=1000", "-oJ", tmpFile, "--wait=3")
	cmd.Env = append(os.Environ(), "PYTHONPATH="+*baseDir)
	out, err := cmd.CombinedOutput()
	log.Printf("[masscan] output: %s, err: %v", string(out), err)

	var hosts []string
	data, err := os.ReadFile(tmpFile)
	if err != nil {
		return hosts
	}
	// Parse masscan JSON output (line-oriented)
	for _, line := range strings.Split(string(data), "\n") {
		if strings.Contains(line, `"status":"open"`) {
			ipRe := regexp.MustCompile(`"ip":"([^"]+)"`)
			if m := ipRe.FindStringSubmatch(line); len(m) > 1 {
				hosts = append(hosts, m[1])
			}
		}
	}
	return hosts
}

// execCertImport imports domains from a certificate by parsing it directly
// (called when job type is "cert")
func execCertImport(certPEM string) {
	assetScanWg.Add(1)
	defer assetScanWg.Done()

	certBlock, err := parsePEM(certPEM)
	if err != nil || len(certBlock) == 0 {
		log.Printf("[cert-import] failed to parse cert: %v", err)
		return
	}

	sha1Hash := sha1.Sum(certBlock)
	certSHA1 := fmt.Sprintf("%X", sha1Hash)

	tlsCert, err := tls.X509KeyPair([]byte(certPEM), []byte(certPEM))
	if err != nil {
		log.Printf("[cert-import] X509KeyPair failed: %v", err)
		return
	}
	if tlsCert.Leaf == nil {
		tlsCert.Leaf, err = x509.ParseCertificate(tlsCert.Certificate[0])
		if err != nil {
			log.Printf("[cert-import] ParseCertificate failed: %v", err)
			return
		}
	}

	domains := extractCertSANs(tlsCert.Leaf)
	if len(domains) == 0 {
		log.Printf("[cert-import] no SANs found in cert %s", certSHA1)
		return
	}

	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		log.Printf("[cert-import] db error: %v", err)
		return
	}
	defer db.Close()

	now := timeNowStr()
	for _, domain := range domains {
		domain = strings.TrimSpace(domain)
		if domain == "" {
			continue
		}
		var certID int64
		db.QueryRow("SELECT id FROM cert_assets WHERE cert_sha1 = ?", certSHA1).Scan(&certID)
		db.Exec(`INSERT OR IGNORE INTO assets
			(asset_type, value, port, scheme, cert_id, status, first_seen, last_seen)
			VALUES ('domain', ?, 443, 'https', ?, 'unknown', ?, ?)`,
			domain, certID, now, now)
	}
	log.Printf("[cert-import] completed: cert %s -> %d domains", certSHA1, len(domains))
}

func goSyncScan(cidrStr string) []string {
	ip, ipnet, err := net.ParseCIDR(cidrStr)
	if err != nil {
		return nil
	}
	var hosts []string
	for ip := ip.Mask(ipnet.Mask); ipnet.Contains(ip); incIP(ip) {
		// Skip common non-web IPs
		lastByte := ip[len(ip)-1]
		if lastByte == 0 || lastByte == 1 || lastByte == 255 {
			continue
		}
		hosts = append(hosts, ip.String())
	}
	return hosts
}

func incIP(ip net.IP) {
	for j := len(ip) - 1; j >= 0; j-- {
		ip[j]++
		if ip[j] > 0 {
			break
		}
	}
}

type hostResult struct {
	IP         string
	Port       int
	Title      string
	Server     string
	StatusCode int
}

func fingerprintHosts(ips []string, ports string) []hostResult {
	portList := []int{80, 443}
	for _, p := range strings.Split(ports, ",") {
		if po, err := strconv.Atoi(strings.TrimSpace(p)); err == nil {
			portList = append(portList, po)
		}
	}

	var results []hostResult
	var mu sync.Mutex
	var wg sync.WaitGroup
	sem := make(chan struct{}, 50) // concurrency limit

	for _, ip := range ips {
		wg.Add(1)
		go func(ip string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			for _, port := range portList {
				h := fingerprintHost(ip, port)
				mu.Lock()
				if h != nil && h.StatusCode > 0 {
					results = append(results, *h)
				}
				mu.Unlock()
			}
		}(ip)
	}
	wg.Wait()
	return results
}

func fingerprintHost(ip string, port int) *hostResult {
	url := fmt.Sprintf("http://%s:%d", ip, port)
	if port == 443 {
		url = fmt.Sprintf("https://%s", ip)
	}

	cli := &http.Client{Timeout: 5 * time.Second}
	resp, err := cli.Get(url)
	if err != nil {
		return &hostResult{IP: ip, Port: port, StatusCode: 0}
	}
	defer resp.Body.Close()

	bodyBytes, _ := io.ReadAll(io.LimitReader(resp.Body, 8192))
	title := extractTitle(string(bodyBytes))
	body := string(bodyBytes)

	server := resp.Header.Get("Server")
	if server == "" {
		server = detectServerFingerprint(body)
	}

	return &hostResult{
		IP:         ip,
		Port:       port,
		Title:      title,
		Server:     server,
		StatusCode: resp.StatusCode,
	}
}

func extractTitle(body string) string {
	re := regexp.MustCompile(`(?i)<title[^>]*>([^<]+)</title>`)
	if m := re.FindStringSubmatch(body); len(m) > 1 {
		return strings.TrimSpace(m[1])
	}
	return ""
}

func detectServerFingerprint(body string) string {
	lower := strings.ToLower(body)
	switch {
	case strings.Contains(lower, "nginx"): return "nginx"
	case strings.Contains(lower, "apache") || strings.Contains(lower, "httpd"): return "apache"
	case strings.Contains(lower, "iis") || strings.Contains(lower, "microsoft"): return "iis"
	case strings.Contains(lower, "tomcat"): return "tomcat"
	case strings.Contains(lower, "jetty"): return "jetty"
	default: return "unknown"
	}
}

// ─── Certificate Import ───────────────────────────────────────────────────────

func importCert(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	var req struct {
		PublicKey  string `json:"public_key"`  // PEM encoded cert (-----BEGIN CERTIFICATE-----)
		PrivateKey string `json:"private_key"` // PEM encoded key (-----BEGIN PRIVATE KEY-----)
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}

	pemCert := strings.TrimSpace(req.PublicKey)
	if pemCert == "" {
		respErr(w, 400, "public_key required")
		return
	}

	// Parse certificate
	certBlock, err := parsePEM(pemCert)
	if err != nil {
		respErr(w, 400, "failed to parse certificate: "+err.Error())
		return
	}

	// Get SHA1 fingerprint
	sha1Hash := sha1.Sum(certBlock)
	certSHA1 := fmt.Sprintf("%X", sha1Hash)

	// Extract cert info
	parsed, err := tls.X509KeyPair([]byte(pemCert), []byte(req.PrivateKey))
	if err != nil {
		// Try with empty private key for read-only cert info
		parsed, err = tls.X509KeyPair([]byte(pemCert), []byte(pemCert))
		if err != nil {
			respErr(w, 400, "failed to parse cert: "+err.Error())
			return
		}
	}

	x509Cert := parsed.Leaf
	if x509Cert == nil {
		respErr(w, 400, "unable to parse certificate chain")
		return
	}

	// Extract all SAN domains
	domains := extractCertSANs(x509Cert)

	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	now := timeNowStr()
	domainsJSON, _ := json.Marshal(domains)

	_, err = db.Exec(`INSERT OR REPLACE INTO cert_assets
		(cert_sha1, cert_subject, cert_issuer, cert_not_before, cert_not_after,
		 san_count, domains, raw_cert, imported_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		certSHA1, x509Cert.Subject.CommonName, x509Cert.Issuer.CommonName,
		x509Cert.NotBefore.Format("2006-01-02"),
		x509Cert.NotAfter.Format("2006-01-02"),
		len(domains), string(domainsJSON), pemCert, now)
	if err != nil {
		respErr(w, 500, "db insert error: "+err.Error())
		return
	}

	// Auto-create assets for each domain in the cert
	insertDomainAssets(db, domains, certSHA1, now)

	respJSON(w, map[string]interface{}{
		"cert_sha1":  certSHA1,
		"domains":    domains,
		"domain_count": len(domains),
		"status":     "imported",
	})
}

func extractCertSANs(cert *x509.Certificate) []string {
	m := make(map[string]bool)
	for _, dns := range cert.DNSNames {
		m[dns] = true
	}
	for _, ip := range cert.IPAddresses {
		m[ip.String()] = true
	}
	domains := []string{}
	for d := range m {
		domains = append(domains, d)
	}
	return domains
}

func insertDomainAssets(db *sql.DB, domains []string, certSHA1, now string) {
	for _, domain := range domains {
		var certID int64
		db.QueryRow("SELECT id FROM cert_assets WHERE cert_sha1 = ?", certSHA1).Scan(&certID)
		_, err := db.Exec(`INSERT OR IGNORE INTO assets
			(asset_type, value, port, scheme, cert_id, status, first_seen, last_seen)
			VALUES ('domain', ?, 443, 'https', ?, 'unknown', ?, ?)`,
			domain, certID, now, now)
		if err != nil {
			log.Printf("[cert-import] insert domain %s error: %v", domain, err)
		}
	}
}

func parsePEM(data string) ([]byte, error) {
	block, _ := pemDecode(data)
	if block == nil {
		return nil, fmt.Errorf("no valid PEM block found")
	}
	return block.Bytes, nil
}

func pemDecode(data string) (*pem.Block, error) {
	block, _ := pem.Decode([]byte(data))
	return block, nil
}

// ─── Snapshots ────────────────────────────────────────────────────────────────

func takeSnapshot(w http.ResponseWriter, r *http.Request, assetID string) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}

	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	// Get asset URL
	var value, scheme string
	var port int
	err = db.QueryRow("SELECT value, scheme, port FROM assets WHERE id = ?", assetID).Scan(&value, &scheme, &port)
	if err != nil {
		respErr(w, 404, "asset not found")
		return
	}

	url := fmt.Sprintf("%s://%s:%d", scheme, value, port)
	if (scheme == "https" && port == 443) || (scheme == "http" && port == 80) {
		url = scheme + "://" + value
	}

	// Fetch page
	cli := &http.Client{Timeout: 15 * time.Second}
	resp, err := cli.Get(url)
	if err != nil {
		respErr(w, 500, "failed to fetch page: "+err.Error())
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(io.LimitReader(resp.Body, 500*1024))
	contentHash := fmt.Sprintf("%X", sha1.Sum(body))
	title := extractTitle(string(body))

	// Get previous snapshot for diff
	var prevHash string
	db.QueryRow("SELECT content_hash FROM asset_snapshots WHERE asset_id = ? ORDER BY scanned_at DESC LIMIT 1", assetID).Scan(&prevHash)

	diffRatio := 0.0
	if prevHash != "" && prevHash != contentHash {
		diffRatio = simpleHashDiff(prevHash, contentHash)
	}

	// Extract meta keywords/description
	keywords := extractMeta(string(body), "keywords")
	description := extractMeta(string(body), "description")

	now := timeNowStr()
	res, err := db.Exec(`INSERT INTO asset_snapshots
		(asset_id, url, title, keywords, description, content_hash, diff_ratio, scanned_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		assetID, url, title, keywords, description, contentHash, diffRatio, now)
	if err != nil {
		respErr(w, 500, "snapshot error: "+err.Error())
		return
	}
	snapshotID, _ := res.LastInsertId()

	// Update asset last_seen and content_hash
	db.Exec("UPDATE assets SET last_seen = ?, content_hash = ?, title = ?, status_code = ? WHERE id = ?",
		now, contentHash, title, resp.StatusCode, assetID)

	// Check for tamper alert
	if diffRatio > 0.3 {
		db.Exec(`INSERT INTO tamper_alerts
			(asset_id, snapshot_id, alert_type, alert_detail, created_at)
			VALUES (?, ?, 'content_changed', ?, ?)`,
			assetID, snapshotID,
			fmt.Sprintf(`{"diff_ratio": %.2f, "prev_hash": "%s", "curr_hash": "%s"}`, diffRatio, prevHash, contentHash),
			now)
	}

	respJSON(w, map[string]interface{}{
		"snapshot_id": snapshotID,
		"content_hash": contentHash,
		"diff_ratio":  diffRatio,
		"status":      "taken",
	})
}

func extractMeta(html, name string) string {
	re := regexp.MustCompile(fmt.Sprintf(`(?i)<meta[^>]+(?:name|property)=["\']%s["\'][^>]+content=["\']([^"\']+)["\']`, name))
	if m := re.FindStringSubmatch(html); len(m) > 1 {
		return m[1]
	}
	// Also try reversed order
	re2 := regexp.MustCompile(fmt.Sprintf(`(?i)<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\']%s["\']`, name))
	if m := re2.FindStringSubmatch(html); len(m) > 1 {
		return m[1]
	}
	return ""
}

func simpleHashDiff(h1, h2 string) float64 {
	if h1 == h2 {
		return 0.0
	}
	// Compare first 8 chars of SHA1 as simple proxy for how different
	var diff int
	for i := 0; i < len(h1) && i < len(h2); i++ {
		if h1[i] != h2[i] {
			diff++
		}
	}
	return math.Min(1.0, float64(diff)/float64(len(h1)))
}

func getSnapshots(w http.ResponseWriter, r *http.Request, assetID string) {
	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	rows, err := db.Query(`SELECT id, asset_id, url, title, keywords, description, content_hash,
		diff_ratio, scanned_at FROM asset_snapshots WHERE asset_id = ? ORDER BY scanned_at DESC LIMIT 30`, assetID)
	if err != nil {
		respErr(w, 500, "query error")
		return
	}
	defer rows.Close()

	var snapshots []AssetSnapshot
	for rows.Next() {
		var s AssetSnapshot
		rows.Scan(&s.ID, &s.AssetID, &s.URL, &s.Title, &s.Keywords, &s.Description,
			&s.ContentHash, &s.DiffRatio, &s.ScannedAt)
		snapshots = append(snapshots, s)
	}
	respJSON(w, map[string]interface{}{"snapshots": snapshots})
}

// ─── Tamper Alerts ────────────────────────────────────────────────────────────

func getTamperAlerts(w http.ResponseWriter, r *http.Request) {
	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	q := r.URL.Query()
	confirmed := q.Get("confirmed") // "0"=pending, "1"=误报, "2"=真实篡改

	sqlStr := `SELECT a.id, a.asset_id, a.snapshot_id, a.alert_type, a.alert_detail,
		a.confirmed, a.confirmed_at, a.confirmed_by, a.created_at,
		ass.value, ass.scheme, ass.port
		FROM tamper_alerts a
		JOIN assets ass ON a.asset_id = ass.id
		WHERE 1=1`
	args := []interface{}{}
	if confirmed != "" {
		sqlStr += " AND a.confirmed = ?"
		args = append(args, confirmed)
	}
	sqlStr += " ORDER BY a.created_at DESC LIMIT 100"

	rows, err := db.Query(sqlStr, args...)
	if err != nil {
		respErr(w, 500, "query error")
		return
	}
	defer rows.Close()

	var alerts []TamperAlert
	for rows.Next() {
		var a TamperAlert
		var scheme string
		var port int
		rows.Scan(&a.ID, &a.AssetID, &a.SnapshotID, &a.AlertType, &a.AlertDetail,
			&a.Confirmed, &a.ConfirmedAt, &a.ConfirmedBy, &a.CreatedAt,
			&a.AssetValue, &scheme, &port)
		a.AssetURL = fmt.Sprintf("%s://%s:%d", scheme, a.AssetValue, port)
		if (scheme == "https" && port == 443) || (scheme == "http" && port == 80) {
			a.AssetURL = scheme + "://" + a.AssetValue
		}
		alerts = append(alerts, a)
	}
	respJSON(w, map[string]interface{}{"alerts": alerts})
}

func confirmAlert(w http.ResponseWriter, r *http.Request, alertID string) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	var req struct {
		Confirmed int    `json:"confirmed"` // 1=误报 2=真实篡改
		ConfirmedBy string `json:"confirmed_by"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	now := timeNowStr()
	db.Exec("UPDATE tamper_alerts SET confirmed = ?, confirmed_at = ?, confirmed_by = ? WHERE id = ?",
		req.Confirmed, now, req.ConfirmedBy, alertID)
	respJSON(w, map[string]string{"status": "updated"})
}

func deleteAlert(w http.ResponseWriter, r *http.Request, alertID string) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	dbPath := filepath.Join(*baseDir, "Libra.db")
	db, _ := openDB(dbPath)
	db.Exec("DELETE FROM tamper_alerts WHERE id = ?", alertID)
	db.Close()
	respJSON(w, map[string]string{"status": "deleted"})
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func timeNowStr() string {
	return time.Now().Format("2006-01-02 15:04:05")
}

func atoi(s string, def int) int {
	n, err := strconv.Atoi(s)
	if err != nil {
		return def
	}
	return n
}
