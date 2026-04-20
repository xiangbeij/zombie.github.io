package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sync"
	"time"

	"github.com/google/uuid"
)

// ─── Config ──────────────────────────────────────────────────────────────────

var (
	Port       = ":5188"
	MaxConcurrent = 10          // max simultaneous scans
	ScanTimeout    = 5 * time.Minute
	BaseDir        = "/opt/Libra"
	DBPath         = "/opt/Libra/Libra.db"
	ReportsDir     = "/opt/Libra/reports"
)

// ─── Data Models ─────────────────────────────────────────────────────────────

type Task struct {
	ID          string    `json:"id"`
	URL         string    `json:"url"`
	ScanType    string    `json:"scan_type"`
	Status      string    `json:"status"` // pending | running | success | error | timeout
	Progress    int       `json:"progress"`
	Result      *ScanResult `json:"result,omitempty"`
	Error       string    `json:"error,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	StartedAt   time.Time `json:"started_at,omitempty"`
	FinishedAt  time.Time `json:"finished_at,omitempty"`
}

type ScanResult struct {
	TaskURL           string   `json:"taskurl"`
	TaskType         string   `json:"tasktype"`
	Status           string   `json:"status"`
	BlacklinkList    []BlacklinkItem `json:"blacklink_list"`
	BackdoorList     []BackdoorItem  `json:"backdoor_list"`
	ViolativelinkList []ViolativeItem `json:"violativelink_list"`
	DiedlinkList     []DiedlinkItem  `json:"diedlink_list"`
	DateTime         string   `json:"datetime"`
}

type BlacklinkItem struct { URL string `json:"url"`; Blacklinkres []string `json:"blacklinkres"`; Master []string `json:"master"` }
type BackdoorItem  struct { URL string `json:"url"`; Backdoorres []string `json:"backdoorres"`; Master []string `json:"master"` }
type ViolativeItem struct { URL string `json:"url"`; Violativelinkres []string `json:"violativelinkres"`; Master []string `json:"master"` }
type DiedlinkItem  struct { URL string `json:"url"`; StatusCode int `json:"status_code"`; Master []string `json:"master"` }

type BatchJob struct {
	ID        string   `json:"id"`
	URLs      []string `json:"urls"`
	ScanType  string   `json:"scan_type"`
	Status    string   `json:"status"` // pending | running | done | paused
	Total     int      `json:"total"`
	Done      int       `json:"done"`
	Success   int       `json:"success"`
	ErrorCount int      `json:"error"`
	TaskIDs   []string `json:"task_ids"`
	CreatedAt time.Time `json:"created_at"`
}

type Stats struct {
	Total, Success, Error, Running int `json:"total,success,error,running"`
}

type ScheduleJob struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	URL       string `json:"url"`
	ScanType  string `json:"scan_type"`
	CronExpr  string `json:"cron_expr"`
	Enabled   bool   `json:"enabled"`
	NextRun   string `json:"next_run,omitempty"`
	LastRun   string `json:"last_run,omitempty"`
	CreatedAt string `json:"created_at"`
}

// ─── In-Memory Store ────────────────────────────────────────────────────────

var (
	taskMu    sync.RWMutex
	Tasks     = make(map[string]*Task)
	batchMu   sync.RWMutex
	Batches   = make(map[string]*BatchJob)
	schedMu   sync.RWMutex
	SchedJobs = make(map[string]*ScheduleJob)
	statsMu   sync.RWMutex
	Stats     = Stats{}
)

// Worker pool
type scanJob struct {
	taskID   string
	url      string
	scanType string
}
var jobQueue = make(chan scanJob, 1000)
var wg sync.WaitGroup

func startWorkerPool() {
	for i := 0; i < MaxConcurrent; i++ {
		go func() {
			for job := range jobQueue {
				runScan(job.taskID, job.url, job.scanType)
			}
		}()
	}
}

func submitScan(taskID, url, scanType string) {
	select {
	case jobQueue <- scanJob{taskID: taskID, url: url, scanType: scanType}:
	default:
		// Queue full — mark as error
		taskMu.Lock()
		if t, ok := Tasks[taskID]; ok {
			t.Status = "error"
			t.Error = "scan queue full, please try later"
		}
		taskMu.Unlock()
	}
}

// ─── Scan Execution ─────────────────────────────────────────────────────────

func runScan(taskID, targetURL, scanType string) {
	wg.Add(1)
	defer wg.Done()

	taskMu.Lock()
	if t, ok := Tasks[taskID]; ok {
		t.Status = "running"
		t.StartedAt = time.Now()
	}
	Stats.Running++
	taskMu.Unlock()

	result, err := executeLibraScan(targetURL, scanType)

	taskMu.Lock()
	defer taskMu.Unlock()

	if t, ok := Tasks[taskID]; ok {
		t.FinishedAt = time.Now()
		t.Progress = 100
		if err != nil {
			t.Status = "error"
			t.Error = err.Error()
			Stats.Error++
		} else {
			t.Status = "success"
			t.Result = result
			Stats.Success++
		}
	}
	Stats.Running++
}

func executeLibraScan(targetURL, scanType string) (*ScanResult, error) {
	cmd := exec.Command("/usr/bin/python3", fmt.Sprintf("%s/Libra.py", BaseDir),
		"-u", targetURL, "-t", scanType)
	cmd.Dir = BaseDir
	cmd.Env = append(os.Environ(), fmt.Sprintf("PYTHONPATH=%s", BaseDir))

	done := make(chan struct{})
	var stdout, stderr []byte

	go func() {
		var err error
		stdout, err = exec.Command("/bin/sh", "-c",
			fmt.Sprintf("PYTHONPATH=%s /usr/bin/python3 %s/Libra.py -u %s -t %s 2>/dev/null",
				BaseDir, BaseDir, targetURL, scanType)).Output()
		if err != nil {
			stderr = []byte(err.Error())
		}
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(ScanTimeout):
		return nil, fmt.Errorf("scan timeout")
	}

	output := string(stdout)
	// Strip ANSI
	re := regexp.MustCompile(`\x1b\[[0-9;]*[a-zA-Z]`)
	output = re.ReplaceAllString(output, "")

	// Find last JSON object
	lines := regexp.MustCompile(`\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}`)
	matches := lines.FindAllString(output, -1)
	var lastJSON string
	for i := len(matches) - 1; i >= 0; i-- {
		m := matches[i]
		if len(m) > 50 {
			lastJSON = m
			break
		}
	}

	if lastJSON == "" {
		return nil, fmt.Errorf("no json output: %s", string(stderr[:min(200, len(stderr))]))
	}

	var result ScanResult
	if err := json.Unmarshal([]byte(lastJSON), &result); err != nil {
		return nil, fmt.Errorf("json parse error: %v", err)
	}
	return &result, nil
}

func min(a, b int) int { if a < b { return a }; return b }

// ─── HTTP Handlers ───────────────────────────────────────────────────────────

func healthHandler(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "ok", "service": "Libra API", "version": "3.0-go",
		"scheduler_available": true, "reportlab_available": true,
	})
}

func statsHandler(w http.ResponseWriter, r *http.Request) {
	statsMu.RLock()
	s := Stats
	statsMu.RUnlock()
	taskMu.RLock()
	running := 0
	for _, t := range Tasks {
		if t.Status == "running" || t.Status == "pending" {
			running++
		}
	}
	taskMu.RUnlock()
	json.NewEncoder(w).Encode(map[string]interface{}{
		"total": s.Total, "success": s.Success, "error": s.Error, "running": running,
	})
}

func scanHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", 405)
		return
	}
	var req struct {
		URL      string `json:"url"`
		ScanType string `json:"scan_type"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json", 400)
		return
	}
	req.URL = sanitizeURL(req.URL)
	if req.URL == "" {
		http.Error(w, "url required", 400)
		return
	}
	if req.ScanType == "" {
		req.ScanType = "HomePage_Scan"
	}

	taskID := uuid.New().String()[:8]
	task := &Task{
		ID:        taskID,
		URL:       req.URL,
		ScanType:  req.ScanType,
		Status:    "pending",
		Progress:  0,
		CreatedAt: time.Now(),
	}
	taskMu.Lock()
	Tasks[taskID] = task
	Stats.Total++
	taskMu.Unlock()

	go submitScan(taskID, req.URL, req.ScanType)

	json.NewEncoder(w).Encode(map[string]interface{}{
		"task_id": taskID, "message": fmt.Sprintf("Scan started: %s -> %s", req.ScanType, req.URL), "status": "accepted",
	})
}

func scanStatusHandler(w http.ResponseWriter, r *http.Request) {
	taskID := filepath.Base(r.URL.Path)
	taskMu.RLock()
	t, ok := Tasks[taskID]
	taskMu.RUnlock()
	if !ok {
		http.Error(w, "task not found", 404)
		return
	}
	jm := map[string]interface{}{
		"id":       t.ID,
		"url":      t.URL,
		"status":   t.Status,
		"progress": t.Progress,
	}
	if t.Error != "" {
		jm["error"] = t.Error
	}
	if t.Result != nil {
		jm["result"] = t.Result
	}
	json.NewEncoder(w).Encode(jm)
}

// Batch scan
func batchHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", 405)
		return
	}
	var req struct {
		URLs     []string `json:"urls"`
		ScanType string   `json:"scan_type"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json", 400)
		return
	}
	if len(req.URLs) == 0 {
		http.Error(w, "urls required", 400)
		return
	}
	if req.ScanType == "" {
		req.ScanType = "HomePage_Scan"
	}

	batchID := uuid.New().String()[:8]
	taskIDs := make([]string, len(req.URLs))

	for i, url := range req.URLs {
		url = sanitizeURL(url)
		if url == "" {
			continue
		}
		taskID := uuid.New().String()[:8]
		taskIDs[i] = taskID
		task := &Task{
			ID: taskID, URL: url, ScanType: req.ScanType,
			Status: "pending", Progress: 0, CreatedAt: time.Now(),
		}
		taskMu.Lock()
		Tasks[taskID] = task
		Stats.Total++
		taskMu.Unlock()
		go submitScan(taskID, url, req.ScanType)
	}

	Batches[batchID] = &BatchJob{
		ID: batchID, URLs: req.URLs, ScanType: req.ScanType,
		Status: "running", Total: len(req.URLs), TaskIDs: taskIDs,
		CreatedAt: time.Now(),
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"batch_id": batchID, "total": len(req.URLs), "message": "batch started",
	})
}

func batchStatusHandler(w http.ResponseWriter, r *http.Request) {
	batchID := filepath.Base(r.URL.Path)
	batchMu.RLock()
	b, ok := Batches[batchID]
	batchMu.RUnlock()
	if !ok {
		http.Error(w, "batch not found", 404)
		return
	}

	taskMu.RLock()
	done, success, errCount := 0, 0, 0
	for _, tid := range b.TaskIDs {
		if t, ok := Tasks[tid]; ok {
			if t.Status == "success" {
				done++
				success++
			} else if t.Status == "error" || t.Status == "timeout" {
				done++
				errCount++
			} else if t.Status == "running" || t.Status == "pending" {
				// still running
			}
		}
	}
	taskMu.RUnlock()

	json.NewEncoder(w).Encode(map[string]interface{}{
		"id": b.ID, "status": b.Status, "total": b.Total,
		"done": done, "success": success, "error": errCount,
	})
}

// Schedule
func scheduleHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		schedMu.RLock()
		list := make([]*ScheduleJob, 0, len(SchedJobs))
		for _, j := range SchedJobs {
			list = append(list, j)
		}
		schedMu.RUnlock()
		json.NewEncoder(w).Encode(map[string]interface{}{"jobs": list})
		return
	}
	if r.Method == http.MethodPost {
		var job ScheduleJob
		if err := json.NewDecoder(r.Body).Decode(&job); err != nil {
			http.Error(w, "invalid json", 400)
			return
		}
		if job.URL == "" || job.CronExpr == "" {
			http.Error(w, "url and cron_expr required", 400)
			return
		}
		job.ID = uuid.New().String()[:8]
		job.Enabled = true
		job.CreatedAt = time.Now().Format(time.RFC3339)
		schedMu.Lock()
		SchedJobs[job.ID] = &job
		schedMu.Unlock()
		json.NewEncoder(w).Encode(map[string]interface{}{"job_id": job.ID, "status": "created"})
		return
	}
	http.Error(w, "method not allowed", 405)
}

func rulesHandler(w http.ResponseWriter, r *http.Request) {
	// Return rule counts from DB
	type RuleCount struct {
		Blacklink    int `json:"blacklink"`
		Backdoor     int `json:"backdoor"`
		Violativelink int `json:"violativelink"`
		WhiteIP      int `json:"whiteip"`
	}
	rc := RuleCount{
		Blacklink: queryDBInt("SELECT COUNT(*) FROM blacklink_rules"),
		Backdoor:  queryDBInt("SELECT COUNT(*) FROM backdoor_rules"),
		Violativelink: queryDBInt("SELECT COUNT(*) FROM violativelink_rules"),
		WhiteIP:   queryDBInt("SELECT COUNT(*) FROM whiteips"),
	}
	json.NewEncoder(w).Encode(rc)
}

// ─── Utilities ─────────────────────────────────────────────────────────────

func sanitizeURL(rawURL string) string {
	url := regexp.MustCompile(`[;&|$`'"<>\\]`).ReplaceAllString(rawURL, "")
	url = regexp.MustCompile(`^https?://`).ReplaceAllString(url, "")
	if len(url) > 500 {
		return url[:500]
	}
	return url
}

func queryDBInt(sql string) int {
	// Simple SQLite query - in production use proper driver
	return 0 // placeholder
}

// ─── Static File Server with API Proxy ──────────────────────────────────────

func proxyHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/api/health" || r.URL.Path == "/api/stats" ||
		r.URL.Path == "/api/scan" || r.URL.Path == "/api/rules" ||
		r.URL.Path == "/api/batch" || r.URL.Path == "/api/schedule" ||
		r.URL.Path == "/api/tasks" {
		// Forward to Go API
		proxyAPI(w, r)
		return
	}
	// Static files
	fs := http.Dir("/opt/Libra/Libra-server/dist")
	if r.URL.Path == "/" {
		r.URL.Path = "/index.html"
	}
	f, err := fs.Open(r.URL.Path[1:])
	if err != nil {
		if os.IsNotExist(err) {
			http.ServeFile(w, r, "/opt/Libra/Libra-server/dist/index.html")
		}
		return
	}
	defer f.Close()
	io.Copy(w, f)
}

func proxyAPI(w http.ResponseWriter, r *http.Request) {
	reqURL := "http://127.0.0.1:5188" + r.URL.Path
	if r.URL.RawQuery != "" {
		reqURL += "?" + r.URL.RawQuery
	}
	req, _ := http.NewRequest(r.Method, reqURL, r.Body)
	req.Header = r.Header.Clone()
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "upstream error", 502)
		return
	}
	defer resp.Body.Close()
	io.Copy(w, resp.Body)
}

// ─── Main ───────────────────────────────────────────────────────────────────

func main() {
	runtime.GOMAXPROCS(runtime.NumCPU())
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	// Initialize
	os.MkdirAll(ReportsDir, 0755)
	startWorkerPool()

	// Seed rand
	rand.Seed(time.Now().UnixNano())

	// Load tasks from disk store on startup
	loadState()

	// HTTP server
	mux := http.NewServeMux()
	mux.HandleFunc("/", proxyHandler)
	mux.HandleFunc("/api/health", healthHandler)
	mux.HandleFunc("/api/stats", statsHandler)
	mux.HandleFunc("/api/scan", scanHandler)
	mux.HandleFunc("/api/scan/", scanStatusHandler)
	mux.HandleFunc("/api/batch", batchHandler)
	mux.HandleFunc("/api/batch/", batchStatusHandler)
	mux.HandleFunc("/api/schedule", scheduleHandler)
	mux.HandleFunc("/api/rules", rulesHandler)

	srv := &http.Server{
		Addr:         Port,
		Handler:      mux,
		ReadTimeout:  60 * time.Second,
		WriteTimeout: 300 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Printf("[Go Libra API] Starting on %s (max %d concurrent scans)", Port, MaxConcurrent)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}
