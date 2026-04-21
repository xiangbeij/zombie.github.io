package main

import (
	"crypto/tls"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net"
	"net/http"
	"net/url"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// 鈹€鈹€鈹€ Site Monitor Models 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

type SiteMonitor struct {
	ID              int64  `json:"id"`
	Name            string `json:"name"`
	URL             string `json:"url"`
	Host            string `json:"host"`
	CheckInterval   int    `json:"check_interval"`
	Enabled         int    `json:"enabled"`
	TimeoutSeconds  int    `json:"timeout_seconds"`
	LastStatus      string `json:"last_status"`
	LastStatusCode  int    `json:"last_status_code"`
	LastRTTMs       int    `json:"last_rtt_ms"`
	LastCheckedAt   string `json:"last_checked_at"`
	LastError       string `json:"last_error"`
	SSlExpiryDate   string `json:"ssl_expiry_date"`
	SSlDaysLeft     int    `json:"ssl_days_left"`
	SSlValid        int    `json:"ssl_valid"`
	CreatedAt       string `json:"created_at"`
	UpdatedAt       string `json:"updated_at"`
}

type MonitorHistory struct {
	ID          int64  `json:"id"`
	MonitorID   int64  `json:"monitor_id"`
	Status      string `json:"status"`
	StatusCode  int    `json:"status_code"`
	RTTMs       int    `json:"rtt_ms"`
	ErrorMsg    string `json:"error_msg"`
	SSlDaysLeft int    `json:"ssl_days_left"`
	CheckedAt   string `json:"checked_at"`
}

type checkResult struct {
	status     string
	statusCode int
	rttMs      int
	errorMsg   string
	sslDays    int
	sslValid   int
	sslExpiry  string
}

// 鈹€鈹€鈹€ Site Monitor Handlers 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func handleSiteMonitor(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	path := strings.TrimPrefix(r.URL.Path, "/api/site-monitor")

	if r.Method == http.MethodGet && path == "" {
		listSiteMonitors(w, r)
		return
	}
	if r.Method == http.MethodPost && path == "" {
		createSiteMonitor(w, r)
		return
	}
	if r.Method == http.MethodGet && path == "/stats" {
		getMonitorStats(w, r)
		return
	}
	if r.Method == http.MethodPost && path == "/check-all" {
		checkAllMonitors(w, r)
		return
	}
	if r.Method == http.MethodDelete && strings.TrimPrefix(path, "/") != "" {
		deleteSiteMonitor(w, r, strings.TrimPrefix(path, "/"))
		return
	}
	if r.Method == http.MethodPut {
		updateSiteMonitor(w, r, strings.TrimPrefix(path, "/"))
		return
	}
	if r.Method == http.MethodPost && strings.HasSuffix(path, "/check") {
		checkSingleMonitor(w, r, strings.TrimSuffix(path, "/check"))
		return
	}
	if r.Method == http.MethodGet && strings.HasPrefix(path, "/") {
		parts := strings.Split(strings.TrimPrefix(path, "/"), "/")
		if len(parts) >= 1 && parts[0] != "" {
			getMonitorHistory(w, r, parts[0])
			return
		}
	}
	respErr(w, 404, "not found")
}

// 鈹€鈹€鈹€ List 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func listSiteMonitors(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	page := atoi(q.Get("page"), 1)
	pageSize := atoi(q.Get("page_size"), 50)
	search := q.Get("search")
	offset := (page - 1) * pageSize

	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	where := "1=1"
	args := []interface{}{}
	if search != "" {
		where += " AND (name LIKE ? OR url LIKE ?)"
		like := "%" + search + "%"
		args = append(args, like, like)
	}

	var total int
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE "+where, args...).Scan(&total)

	sqlStr := fmt.Sprintf(`SELECT id, name, url, host, check_interval, enabled, timeout_seconds,
		last_status, last_status_code, last_rtt_ms, last_checked_at, last_error,
		ssl_expiry_date, ssl_days_left, ssl_valid, created_at, updated_at
		FROM site_monitors WHERE %s ORDER BY id DESC LIMIT ? OFFSET ?`, where)
	args = append(args, pageSize, offset)

	rows, err := db.Query(sqlStr, args...)
	if err != nil {
		respErr(w, 500, "query error: "+err.Error())
		return
	}
	defer rows.Close()

	var monitors []SiteMonitor
	for rows.Next() {
		var m SiteMonitor
		rows.Scan(&m.ID, &m.Name, &m.URL, &m.Host, &m.CheckInterval, &m.Enabled, &m.TimeoutSeconds,
			&m.LastStatus, &m.LastStatusCode, &m.LastRTTMs, &m.LastCheckedAt, &m.LastError,
			&m.SSlExpiryDate, &m.SSlDaysLeft, &m.SSlValid, &m.CreatedAt, &m.UpdatedAt)
		monitors = append(monitors, m)
	}

	respJSON(w, map[string]interface{}{
		"monitors":    monitors,
		"total":       total,
		"page":        page,
		"page_size":   pageSize,
		"total_pages": int(math.Ceil(float64(total) / float64(pageSize))),
	})
}

// 鈹€鈹€鈹€ Create 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func createSiteMonitor(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Name           string `json:"name"`
		URL            string `json:"url"`
		CheckInterval  int    `json:"check_interval"`
		TimeoutSeconds int    `json:"timeout_seconds"`
		Enabled        int    `json:"enabled"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}
	if req.Name == "" || req.URL == "" {
		respErr(w, 400, "name and url required")
		return
	}
	if !strings.HasPrefix(req.URL, "http") {
		req.URL = "https://" + req.URL
	}
	u, err := url.Parse(req.URL)
	if err != nil {
		respErr(w, 400, "invalid url")
		return
	}
	host := u.Host
	if req.CheckInterval == 0 {
		req.CheckInterval = 60
	}
	if req.TimeoutSeconds == 0 {
		req.TimeoutSeconds = 10
	}
	if req.Enabled == 0 {
		req.Enabled = 1
	}

	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	now := timeNowStr()
	res, err := db.Exec(`INSERT INTO site_monitors
		(name, url, host, check_interval, enabled, timeout_seconds, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		req.Name, req.URL, host, req.CheckInterval, req.Enabled, req.TimeoutSeconds, now, now)
	if err != nil {
		respErr(w, 500, "insert error: "+err.Error())
		return
	}
	id, _ := res.LastInsertId()

	go runMonitorCheck(id, req.URL, req.TimeoutSeconds)

	respJSON(w, map[string]interface{}{"id": id, "status": "created"})
}

// 鈹€鈹€鈹€ Update 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func updateSiteMonitor(w http.ResponseWriter, r *http.Request, idStr string) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	var req struct {
		Name           string `json:"name"`
		URL            string `json:"url"`
		CheckInterval  int    `json:"check_interval"`
		TimeoutSeconds int    `json:"timeout_seconds"`
		Enabled        int    `json:"enabled"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	now := timeNowStr()
	host := req.URL
	if strings.Contains(req.URL, "://") {
		host = strings.SplitN(req.URL, "://", 2)[1]
	}
	_, err = db.Exec(`UPDATE site_monitors SET
		name=?, url=?, host=?, check_interval=?, enabled=?, timeout_seconds=?, updated_at=?
		WHERE id=?`,
		req.Name, req.URL, host, req.CheckInterval,
		req.Enabled, req.TimeoutSeconds, now, idStr)
	if err != nil {
		respErr(w, 500, "update error")
		return
	}
	respJSON(w, map[string]string{"status": "updated"})
}

// 鈹€鈹€鈹€ Delete 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func deleteSiteMonitor(w http.ResponseWriter, r *http.Request, idStr string) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	dbPath := filepath.Join(*baseDir, "orion.db")
	db, _ := openDB(dbPath)
	db.Exec("DELETE FROM site_monitors WHERE id = ?", idStr)
	db.Exec("DELETE FROM site_monitor_history WHERE monitor_id = ?", idStr)
	db.Close()
	respJSON(w, map[string]string{"status": "deleted"})
}

// 鈹€鈹€鈹€ Stats 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func getMonitorStats(w http.ResponseWriter, r *http.Request) {
	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	var total, online, offline, errorCount, unknown int
	var sslWarn, sslExpired int
	var avgRTT int
	db.QueryRow("SELECT COUNT(*) FROM site_monitors").Scan(&total)
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE last_status='online'").Scan(&online)
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE last_status='offline'").Scan(&offline)
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE last_status='error'").Scan(&errorCount)
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE last_status='unknown'").Scan(&unknown)
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE ssl_valid=1 AND ssl_days_left <= 30 AND ssl_days_left > 0").Scan(&sslWarn)
	db.QueryRow("SELECT COUNT(*) FROM site_monitors WHERE ssl_valid=1 AND ssl_days_left <= 0").Scan(&sslExpired)
	db.QueryRow("SELECT COALESCE(AVG(last_rtt_ms), 0) FROM site_monitors WHERE last_status='online'").Scan(&avgRTT)

	respJSON(w, map[string]interface{}{
		"total":       total,
		"online":      online,
		"offline":     offline,
		"error":       errorCount,
		"unknown":     unknown,
		"ssl_warn":    sslWarn,
		"ssl_expired": sslExpired,
		"avg_rtt_ms":   avgRTT,
	})
}

// 鈹€鈹€鈹€ Check Single 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func checkSingleMonitor(w http.ResponseWriter, r *http.Request, idStr string) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	var monitorURL string
	var timeout int
	err = db.QueryRow("SELECT url, timeout_seconds FROM site_monitors WHERE id = ?", idStr).Scan(&monitorURL, &timeout)
	if err != nil {
		respErr(w, 404, "monitor not found")
		return
	}

	result := doCheck(monitorURL, timeout)
	saveMonitorResult(db, idStr, result)

	respJSON(w, map[string]interface{}{
		"status":      result.status,
		"status_code": result.statusCode,
		"rtt_ms":      result.rttMs,
		"error":       result.errorMsg,
		"ssl_days":    result.sslDays,
		"checked_at":  timeNowStr(),
	})
}

// 鈹€鈹€鈹€ Check All 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func checkAllMonitors(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	rows, err := db.Query("SELECT id, url, timeout_seconds FROM site_monitors WHERE enabled=1")
	if err != nil {
		respErr(w, 500, "query error")
		return
	}
	defer rows.Close()

	type resultPair struct {
		ID     int64
		Result checkResult
	}
	var wg sync.WaitGroup
	results := make(chan resultPair, 50)
	sem := make(chan struct{}, 20)

	for rows.Next() {
		var id int64
		var monitorURL string
		var timeout int
		rows.Scan(&id, &monitorURL, &timeout)
		wg.Add(1)
		go func(mid int64, murl string, to int) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			r := doCheck(murl, to)
			results <- resultPair{ID: mid, Result: r}
		}(id, monitorURL, timeout)
	}
	go func() {
		wg.Wait()
		close(results)
	}()

	saved := 0
	for rp := range results {
		db2, _ := openDB(dbPath)
		saveMonitorResult(db2, fmt.Sprintf("%d", rp.ID), rp.Result)
		db2.Close()
		saved++
	}

	respJSON(w, map[string]interface{}{
		"status":     "completed",
		"checked":    saved,
		"checked_at": timeNowStr(),
	})
}

// 鈹€鈹€鈹€ History 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func getMonitorHistory(w http.ResponseWriter, r *http.Request, idStr string) {
	limit := atoi(r.URL.Query().Get("limit"), 20)

	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		respErr(w, 500, "db error")
		return
	}
	defer db.Close()

	rows, err := db.Query(`SELECT id, monitor_id, status, status_code, rtt_ms, error_msg,
		ssl_days_left, checked_at FROM site_monitor_history
		WHERE monitor_id = ? ORDER BY checked_at DESC LIMIT ?`, idStr, limit)
	if err != nil {
		respErr(w, 500, "query error")
		return
	}
	defer rows.Close()

	var history []MonitorHistory
	for rows.Next() {
		var h MonitorHistory
		rows.Scan(&h.ID, &h.MonitorID, &h.Status, &h.StatusCode, &h.RTTMs,
			&h.ErrorMsg, &h.SSlDaysLeft, &h.CheckedAt)
		history = append(history, h)
	}
	respJSON(w, map[string]interface{}{"history": history})
}

// 鈹€鈹€鈹€ Core Check Logic 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func runMonitorCheck(id int64, monitorURL string, timeoutSeconds int) {
	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		return
	}
	defer db.Close()
	result := doCheck(monitorURL, timeoutSeconds)
	saveMonitorResult(db, fmt.Sprintf("%d", id), result)
}

func doCheck(targetURL string, timeoutSeconds int) checkResult {
	if timeoutSeconds <= 0 {
		timeoutSeconds = 10
	}
	start := time.Now()

	cli := &http.Client{
		Timeout: time.Duration(timeoutSeconds) * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}

	result := checkResult{status: "error", statusCode: 0, sslDays: -1, sslValid: -1}

	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		result.errorMsg = "invalid url"
		return result
	}
	req.Header.Set("User-Agent", "ORION-Monitor/1.0")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,*/*")

	resp, err := cli.Do(req)
	if err != nil {
		result.status = "offline"
		result.errorMsg = err.Error()
		if strings.HasPrefix(targetURL, "https") {
			sslDays, sslExpiry := checkSSL(targetURL, timeoutSeconds)
			result.sslDays = sslDays
			result.sslExpiry = sslExpiry
			if sslDays >= 0 {
				result.sslValid = 1
			} else {
				result.sslValid = 0
			}
		}
		return result
	}
	defer resp.Body.Close()

	result.rttMs = int(time.Since(start).Milliseconds())
	result.statusCode = resp.StatusCode

	if resp.StatusCode >= 200 && resp.StatusCode < 400 {
		result.status = "online"
	} else if resp.StatusCode >= 400 {
		result.status = "error"
	}

	io.Copy(io.Discard, io.LimitReader(resp.Body, 1024))

	if strings.HasPrefix(targetURL, "https") {
		sslDays, sslExpiry := checkSSL(targetURL, timeoutSeconds)
		result.sslDays = sslDays
		result.sslExpiry = sslExpiry
		result.sslValid = 1
		if sslDays <= 0 && sslDays != -1 {
			result.sslValid = 0
		}
	}

	return result
}

func checkSSL(targetURL string, timeoutSeconds int) (daysLeft int, expiryDate string) {
	u, err := url.Parse(targetURL)
	if err != nil {
		return -1, ""
	}
	host := u.Host
	if strings.Contains(host, ":") {
		host = strings.Split(host, ":")[0]
	}

	dialer := &net.Dialer{Timeout: time.Duration(timeoutSeconds) * time.Second}
	conn, err := tls.DialWithDialer(dialer, "tcp", host+":443", &tls.Config{
		InsecureSkipVerify: true,
	})
	if err != nil {
		return -1, ""
	}
	defer conn.Close()

	certs := conn.ConnectionState().PeerCertificates
	if len(certs) == 0 {
		return -1, ""
	}
	cert := certs[0]
	expiryDate = cert.NotAfter.Format("2006-01-02")
	daysLeft = int(time.Until(cert.NotAfter).Hours() / 24)
	return daysLeft, expiryDate
}

func saveMonitorResult(db *sql.DB, idStr string, result checkResult) {
	now := timeNowStr()

	sslValid := -1
	if result.status == "online" || result.status == "error" {
		sslValid = result.sslValid
	}

	_, err := db.Exec(`UPDATE site_monitors SET
		last_status=?, last_status_code=?, last_rtt_ms=?,
		last_checked_at=?, last_error=?, ssl_expiry_date=?,
		ssl_days_left=?, ssl_valid=?, updated_at=?
		WHERE id=?`,
		result.status, result.statusCode, result.rttMs,
		now, result.errorMsg, result.sslExpiry,
		result.sslDays, sslValid, now, idStr)
	if err != nil {
		log.Printf("[site-monitor] update error: %v", err)
	}

	_, err = db.Exec(`INSERT INTO site_monitor_history
		(monitor_id, status, status_code, rtt_ms, error_msg, ssl_days_left, checked_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		idStr, result.status, result.statusCode, result.rttMs,
		result.errorMsg, result.sslDays, now)
	if err != nil {
		log.Printf("[site-monitor] history insert error: %v", err)
	}
}

// 鈹€鈹€鈹€ Background Monitor Loop 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func startMonitorLoop() {
	ticker := time.NewTicker(30 * time.Second)
	for range ticker.C {
		runEnabledMonitors()
	}
}

func runEnabledMonitors() {
	dbPath := filepath.Join(*baseDir, "orion.db")
	db, err := openDB(dbPath)
	if err != nil {
		return
	}
	defer db.Close()

	rows, err := db.Query("SELECT id, url, timeout_seconds FROM site_monitors WHERE enabled=1")
	if err != nil {
		return
	}
	defer rows.Close()

	type monitorJob struct {
		id      int64
		url     string
		timeout int
	}
	var toRun []monitorJob
	for rows.Next() {
		var m monitorJob
		rows.Scan(&m.id, &m.url, &m.timeout)
		toRun = append(toRun, m)
	}

	var wg sync.WaitGroup
	sem := make(chan struct{}, 10)
	for _, job := range toRun {
		wg.Add(1)
		go func(id int64, u string, to int) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			runMonitorCheck(id, u, to)
		}(job.id, job.url, job.timeout)
	}
	wg.Wait()
}
