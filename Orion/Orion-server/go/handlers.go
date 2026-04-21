package main

import (
	"database/sql"
	
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

func setCORS(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	respJSON(w, map[string]interface{}{
		"status":    "ok",
		"service":   "ORION API",
		"version":   "5.0-go",
		"scheduler": true,
		"workers":   *maxConcurrent,
	})
}

func handleStats(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	StatsMu.RLock()
	s := Stats
	StatsMu.RUnlock()
	TasksMu.RLock()
	running := 0
	for _, t := range Tasks {
		if t.Status == "running" || t.Status == "pending" {
			running++
		}
	}
	TasksMu.RUnlock()
	respJSON(w, map[string]interface{}{
		"total": s.Total, "success": s.Success, "error": s.Error, "running": running,
	})
}

// 鈹€鈹€鈹€ Threat Summary (aggregated from completed scan results) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

// handleAssetsProxy forwards asset requests to the Flask assets API on port 5187
func handleAssetsProxy(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}

	// Build target URL (Flask listens on 5187)
	flaskURL := "http://127.0.0.1:5187" + r.URL.Path
	if r.URL.RawQuery != "" {
		flaskURL += "?" + r.URL.RawQuery
	}

	req, err := http.NewRequest(r.Method, flaskURL, r.Body)
	if err != nil {
		respErr(w, 502, "bad request")
		return
	}
	req.Header.Set("Content-Type", r.Header.Get("Content-Type"))
	req.Header.Set("Authorization", r.Header.Get("Authorization"))

	client := &http.Client{Timeout: 15 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		respErr(w, 502, "Flask assets API unreachable: "+err.Error())
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	for k, v := range resp.Header {
		if k == "Content-Type" || k == "Content-Length" {
			continue
		}
		w.Header().Set(k, v[0])
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	w.Write(body)
}

func handleThreatSummary(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}

	TasksMu.RLock()
	var totalBlacklinks, totalBackdoors, totalViolations, totalDiedlinks int
	var weekBlacklinks, weekBackdoors, weekViolations int
	weekAgo := time.Now().AddDate(0, 0, -7)
	blacklinkSet := make(map[string]int)  // url -> count

	for _, t := range Tasks {
		if t.Status != "success" || t.Result == nil {
			continue
		}
		res := t.Result
		blacklinks := 0
		backdoors := 0
		violations := 0
		diedlinks := 0

		for _, l := range res.BlacklinkList {
			blacklinks += len(l.Results)
			for _, r := range l.Results {
				if r != "" {
					blacklinkSet[r]++
				}
			}
		}
		for _, l := range res.BackdoorList {
			backdoors += len(l.Results)
		}
		for _, l := range res.ViolativelinkList {
			violations += len(l.Results)
		}
		for range res.DiedlinkList {
			 diedlinks++
		}

		totalBlacklinks += blacklinks
		totalBackdoors += backdoors
		totalViolations += violations
		totalDiedlinks += diedlinks

		if t.FinishedAt.After(weekAgo) {
			weekBlacklinks += blacklinks
			weekBackdoors += backdoors
			weekViolations += violations
		}
	}
	TasksMu.RUnlock()

	// Top threats
	topBlacklinks := []map[string]interface{}{}
	for r, c := range blacklinkSet {
		topBlacklinks = append(topBlacklinks, map[string]interface{}{"pattern": r, "count": c})
	}
	// Sort by count desc, take top 10
	for i := 0; i < len(topBlacklinks)-1; i++ {
		for j := i + 1; j < len(topBlacklinks); j++ {
			if topBlacklinks[j]["count"].(int) > topBlacklinks[i]["count"].(int) {
				topBlacklinks[i], topBlacklinks[j] = topBlacklinks[j], topBlacklinks[i]
			}
		}
	}
	if len(topBlacklinks) > 10 {
		topBlacklinks = topBlacklinks[:10]
	}

	respJSON(w, map[string]interface{}{
		"total_blacklinks":  totalBlacklinks,
		"total_backdoors":   totalBackdoors,
		"total_violations":  totalViolations,
		"total_diedlinks":   totalDiedlinks,
		"week_blacklinks":   weekBlacklinks,
		"week_backdoors":    weekBackdoors,
		"week_violations":   weekViolations,
		"top_blacklink_patterns": topBlacklinks,
	})
}

// 鈹€鈹€鈹€ Paginated Tasks 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

func handleTasksPaginated(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}

	q := r.URL.Query()
	page := atoi(q.Get("page"), 1)
	pageSize := atoi(q.Get("page_size"), 20)
	status := q.Get("status")
	search := q.Get("search")
	if pageSize > 100 {
		pageSize = 100
	}
	offset := (page - 1) * pageSize

	TasksMu.RLock()
	filtered := []*Task{}
	for _, t := range Tasks {
		match := true
		if status != "" && t.Status != status {
			match = false
		}
		if search != "" && !strings.Contains(t.URL, search) {
			match = false
		}
		if match {
			filtered = append(filtered, t)
		}
	}

	// Sort by created_at desc
	for i := 0; i < len(filtered)-1; i++ {
		for j := i + 1; j < len(filtered); j++ {
			if filtered[j].CreatedAt.After(filtered[i].CreatedAt) {
				filtered[i], filtered[j] = filtered[j], filtered[i]
			}
		}
	}

	total := len(filtered)
	end := offset + pageSize
	if end > total {
		end = total
	}
	if offset >= total {
		filtered = []*Task{}
	} else {
		filtered = filtered[offset:end]
	}
	TasksMu.RUnlock()

	// Build response with threat counts
	tasks := make([]map[string]interface{}, 0, len(filtered))
	for _, t := range filtered {
		m := map[string]interface{}{
			"id":          t.ID,
			"url":         t.URL,
			"scan_type":   t.ScanType,
			"status":      t.Status,
			"progress":    t.Progress,
			"error":       t.Error,
			"created_at":  t.CreatedAt.Format(time.RFC3339),
			"finished_at": "",
			"blacklink_count":  0,
			"backdoor_count":   0,
			"violative_count":  0,
			"diedlink_count":    0,
		}
		if !t.FinishedAt.IsZero() {
			m["finished_at"] = t.FinishedAt.Format(time.RFC3339)
		}
		if t.Result != nil {
			m["blacklink_count"] = countLinkResults(t.Result.BlacklinkList)
			m["backdoor_count"] = countLinkResults(t.Result.BackdoorList)
			m["violative_count"] = countLinkResults(t.Result.ViolativelinkList)
			m["diedlink_count"] = len(t.Result.DiedlinkList)
		}
		tasks = append(tasks, m)
	}

	respJSON(w, map[string]interface{}{
		"tasks":       tasks,
		"total":       total,
		"page":        page,
		"page_size":   pageSize,
		"total_pages": (total + pageSize - 1) / pageSize,
	})
}

func countLinkResults(list []Link) int {
	c := 0
	for _, l := range list {
		c += len(l.Results)
	}
	return c
}

type scanReq struct {
	URL      string `json:"url"`
	ScanType string `json:"scan_type"`
}

func handleScan(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	if r.Method != http.MethodPost {
		respErr(w, 405, "method not allowed")
		return
	}
	var req scanReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}
	req.URL = strings.TrimSpace(req.URL)
	if req.URL == "" {
		respErr(w, 400, "url required")
		return
	}
	req.URL = sanitizeURL(req.URL)
	scanType := req.ScanType
	if scanType == "" {
		scanType = "HomePage_Scan"
	}
	if !validScanType(scanType) {
		respErr(w, 400, "invalid scan_type")
		return
	}
	taskID := uuid.New().String()[:8]
	task := &Task{
		ID: taskID, URL: req.URL, ScanType: scanType,
		Status: "pending", Progress: 0, CreatedAt: time.Now(),
	}
	TasksMu.Lock()
	Tasks[taskID] = task
	Stats.Total++
	TasksMu.Unlock()
	go submitScan(taskID, req.URL, scanType)
	go saveState()
	respJSON(w, map[string]interface{}{
		"task_id": taskID,
		"message": fmt.Sprintf("Scan started: %s -> %s", scanType, req.URL),
		"status":  "accepted",
	})
}

func handleScanStatus(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	// POST /api/scan/:id/pause
	if r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/pause") {
		taskID := sanitizePath(strings.TrimSuffix(r.URL.Path, "/pause"))
		TasksMu.Lock()
		defer TasksMu.Unlock()
		if t, ok := Tasks[taskID]; ok {
			if t.Status == "running" || t.Status == "pending" {
				t.Status = "paused"
				t.Error = "鐢ㄦ埛鏆傚仠"
				t.FinishedAt = time.Now()
				go saveState()
				respJSON(w, map[string]string{"status": "paused", "task_id": taskID})
				return
			}
			respErr(w, 400, "task cannot be paused in current state: "+t.Status)
			return
		}
		respErr(w, 404, "task not found")
		return
	}

	taskID := sanitizePath(r.URL.Path)
	TasksMu.RLock()
	t, ok := Tasks[taskID]
	TasksMu.RUnlock()
	if !ok {
		respErr(w, 404, "task not found")
		return
	}
	resp := map[string]interface{}{
		"id": t.ID, "url": t.URL, "scan_type": t.ScanType,
		"status": t.Status, "progress": t.Progress,
	}
	if t.Error != "" {
		resp["error"] = t.Error
	}
	if t.Result != nil {
		resp["result"] = t.Result
	}
	respJSON(w, resp)
}

func handleTasks(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	TasksMu.RLock()
	list := make([]*Task, 0, len(Tasks))
	for _, t := range Tasks {
		list = append(list, t)
	}
	TasksMu.RUnlock()
	respJSON(w, map[string]interface{}{"tasks": list})
}

func handleTaskDelete(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	taskID := sanitizePath(r.URL.Path)
	TasksMu.Lock()
	delete(Tasks, taskID)
	TasksMu.Unlock()
	respJSON(w, map[string]string{"status": "deleted"})
}

type batchReq struct {
	URLs     []string `json:"urls"`
	ScanType string   `json:"scan_type"`
}

func handleBatch(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	// GET /api/batch - list all batches
	if r.Method == http.MethodGet {
		BatchesMu.RLock()
		list := make([]*Batch, 0, len(Batches))
		for _, b := range Batches {
			list = append(list, b)
		}
		BatchesMu.RUnlock()
		TasksMu.RLock()
		result := make([]map[string]interface{}, 0, len(list))
		for _, b := range list {
			done, success, errCount := 0, 0, 0
			for _, tid := range b.TaskIDs {
				if t, ok := Tasks[tid]; ok {
					switch t.Status {
					case "success":
						done++
						success++
					case "error", "timeout":
						done++
						errCount++
					}
				}
			}
			result = append(result, map[string]interface{}{
				"id": b.ID, "scan_type": b.ScanType,
				"total": b.Total, "success": success, "error": errCount,
				"completed": done, "status": b.Status,
				"created_at": b.CreatedAt.Format(time.RFC3339),
			})
		}
		TasksMu.RUnlock()
		respJSON(w, map[string]interface{}{"batches": result})
		return
	}
	if r.Method != http.MethodPost {
		respErr(w, 405, "method not allowed")
		return
	}
	var req batchReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}
	if len(req.URLs) == 0 {
		respErr(w, 400, "urls required")
		return
	}
	scanType := req.ScanType
	if scanType == "" {
		scanType = "HomePage_Scan"
	}
	seen := make(map[string]bool)
	unique := make([]string, 0, len(req.URLs))
	for _, u := range req.URLs {
		u = strings.TrimSpace(sanitizeURL(u))
		if u == "" || seen[u] {
			continue
		}
		seen[u] = true
		unique = append(unique, u)
	}
	batchID := uuid.New().String()[:8]
	taskIDs := make([]string, len(unique))
	TasksMu.Lock()
	for i, url := range unique {
		tid := uuid.New().String()[:8]
		taskIDs[i] = tid
		Tasks[tid] = &Task{
			ID: tid, URL: url, ScanType: scanType,
			Status: "pending", Progress: 0, CreatedAt: time.Now(),
		}
		Stats.Total++
	}
	TasksMu.Unlock()
	BatchesMu.Lock()
	Batches[batchID] = &Batch{
		ID: batchID, URLs: unique, ScanType: scanType,
		Status: "running", Total: len(unique), TaskIDs: taskIDs,
		CreatedAt: time.Now(),
	}
	BatchesMu.Unlock()
	for i, url := range unique {
		go submitScan(taskIDs[i], url, scanType)
	}
	go saveState()
	respJSON(w, map[string]interface{}{
		"batch_id": batchID,
		"total":    len(unique),
		"message":  "batch started",
	})
}

func handleBatchStatus(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	batchID := sanitizePath(r.URL.Path)

	// DELETE /api/batch/:id
	if r.Method == http.MethodDelete {
		BatchesMu.Lock()
		delete(Batches, batchID)
		BatchesMu.Unlock()
		respJSON(w, map[string]string{"status": "deleted"})
		return
	}

	BatchesMu.RLock()
	b, ok := Batches[batchID]
	BatchesMu.RUnlock()
	if !ok {
		respErr(w, 404, "batch not found")
		return
	}
	TasksMu.RLock()
	done, success, errCount := 0, 0, 0
	for _, tid := range b.TaskIDs {
		if t, ok := Tasks[tid]; ok {
			switch t.Status {
			case "success":
				done++
				success++
			case "error", "timeout":
				done++
				errCount++
			}
		}
	}
	TasksMu.RUnlock()
	BatchesMu.Lock()
	b.Completed, b.Success, b.Error = done, success, errCount
	if done >= b.Total {
		b.Status = "done"
	}
	BatchesMu.Unlock()
	respJSON(w, map[string]interface{}{
		"id": b.ID, "status": b.Status, "total": b.Total,
		"completed": done, "success": success, "error": errCount,
		"task_ids": b.TaskIDs,
	})
}

type scheduleReq struct {
	Name     string `json:"name"`
	URL      string `json:"url"`
	ScanType string `json:"scan_type"`
	CronExpr string `json:"cron_expr"`
}

func handleSchedule(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	switch r.Method {
	case http.MethodGet:
		SchedMu.RLock()
		list := make([]*ScheduleJob, 0, len(SchedJobs))
		for _, j := range SchedJobs {
			list = append(list, j)
		}
		SchedMu.RUnlock()
		respJSON(w, map[string]interface{}{"jobs": list})
		return
	case http.MethodPost:
		var req scheduleReq
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			respErr(w, 400, "invalid json")
			return
		}
		req.URL = strings.TrimSpace(sanitizeURL(req.URL))
		if req.URL == "" || req.CronExpr == "" {
			respErr(w, 400, "url and cron_expr required")
			return
		}
		if req.Name == "" {
			req.Name = req.URL
		}
		scanType := req.ScanType
		if scanType == "" {
			scanType = "HomePage_Scan"
		}
		expr := req.CronExpr
		fields := strings.Fields(expr)
		if len(fields) != 5 && len(fields) != 6 {
			respErr(w, 400, "invalid cron expr: need 5 or 6 fields")
			return
		}
		entryID, err := sched.AddFunc(expr, func() {
			runScheduledScan(req.URL, scanType)
		})
		if err != nil {
			respErr(w, 400, "invalid cron expr: "+err.Error())
			return
		}
		job := &ScheduleJob{
			ID: uuid.New().String()[:8], Name: req.Name,
			URL: req.URL, ScanType: scanType, CronExpr: expr,
			Enabled: true, CreatedAt: time.Now(), CronEntryID: entryID,
		}
		SchedMu.Lock()
		SchedJobs[job.ID] = job
		SchedMu.Unlock()
		go saveState()
		respJSON(w, map[string]interface{}{"job_id": job.ID, "status": "created"})
		return
	}
	respErr(w, 405, "method not allowed")
}

func handleScheduleOp(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	parts := strings.SplitN(strings.TrimPrefix(r.URL.Path, "/api/schedule/"), "/", 2)
	jobID := parts[0]
	SchedMu.Lock()
	defer SchedMu.Unlock()
	job, ok := SchedJobs[jobID]
	if !ok {
		respErr(w, 404, "job not found")
		return
	}
	switch r.Method {
	case http.MethodGet:
		respJSON(w, job)
		return
	case http.MethodDelete:
		if job.CronEntryID > 0 {
			sched.Remove(job.CronEntryID)
		}
		delete(SchedJobs, jobID)
		go saveState()
		respJSON(w, map[string]string{"status": "deleted"})
		return
	case http.MethodPut:
		var req struct {
			Enabled  *bool  `json:"enabled"`
			CronExpr string `json:"cron_expr"`
		}
		json.NewDecoder(r.Body).Decode(&req)
		if req.Enabled != nil {
			job.Enabled = *req.Enabled
			if job.CronEntryID > 0 {
				sched.Remove(job.CronEntryID)
				job.CronEntryID = 0
			}
			if job.Enabled {
				entryID, err := sched.AddFunc(job.CronExpr, func() {
					runScheduledScan(job.URL, job.ScanType)
				})
				if err == nil {
					job.CronEntryID = entryID
				}
			}
		}
		if req.CronExpr != "" && req.CronExpr != job.CronExpr {
			if job.CronEntryID > 0 {
				sched.Remove(job.CronEntryID)
			}
			job.CronExpr = req.CronExpr
			entryID, err := sched.AddFunc(job.CronExpr, func() {
				runScheduledScan(job.URL, job.ScanType)
			})
			if err == nil {
				job.CronEntryID = entryID
			}
		}
		go saveState()
		respJSON(w, job)
		return
	}
	respErr(w, 405, "method not allowed")
}

func runScheduledScan(url, scanType string) {
	taskID := uuid.New().String()[:8]
	task := &Task{
		ID: taskID, URL: url, ScanType: scanType,
		Status: "pending", Progress: 0, CreatedAt: time.Now(),
	}
	TasksMu.Lock()
	Tasks[taskID] = task
	Stats.Total++
	TasksMu.Unlock()
	submitScan(taskID, url, scanType)
	go saveState()
	log.Printf("[scheduler] triggered scan %s for %s", taskID, url)
}

func handleRules(w http.ResponseWriter, r *http.Request) {
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

	// GET /api/rules - counts only (backward compatible)
	if r.Method == http.MethodGet && r.URL.Query().Get("list") != "1" && !strings.HasSuffix(r.URL.Path, "/list") {
		respJSON(w, map[string]interface{}{
			"blacklink_rules":     queryInt(db, "SELECT COUNT(*) FROM blacklink_rules"),
			"backdoor_rules":      queryInt(db, "SELECT COUNT(*) FROM backdoor_rules"),
			"violativelink_rules": queryInt(db, "SELECT COUNT(*) FROM violativelink_rules"),
			"backdoor_paths":      queryInt(db, "SELECT COUNT(*) FROM backdoor_paths"),
		})
		return
	}

	// GET /api/rules/list - full rule arrays
	if strings.HasSuffix(r.URL.Path, "/list") || r.URL.Query().Get("list") == "1" {
		respJSON(w, map[string]interface{}{
			"blacklink_rules":     queryRules(db, "SELECT re, mark FROM blacklink_rules"),
			"backdoor_rules":      queryRules(db, "SELECT re, mark FROM backdoor_rules"),
			"violativelink_rules": queryRules(db, "SELECT re, mark FROM violativelink_rules"),
			"backdoor_paths":       queryStrSlice(db, "SELECT path FROM backdoor_paths"),
		})
		return
	}

	respErr(w, 400, "invalid request")
}

func queryRules(db *sql.DB, sqlq string) [][]string {
	rows, err := db.Query(sqlq)
	if err != nil {
		log.Printf("[rules] query error: %v | sql: %s", err, sqlq)
		return [][]string{}
	}
	defer rows.Close()
	var result [][]string
	for rows.Next() {
		var pat, mark string
		if err := rows.Scan(&pat, &mark); err == nil {
			result = append(result, []string{pat, mark})
		}
	}
	log.Printf("[rules] queryRules returned %d rows", len(result))
	return result
}


func queryInt(db *sql.DB, sqlq string) int {
	var n int
	if err := db.QueryRow(sqlq).Scan(&n); err != nil {
		return 0
	}
	return n
}
func queryStrSlice(db *sql.DB, sqlq string) []string {
	rows, err := db.Query(sqlq)
	if err != nil {
		return []string{}
	}
	defer rows.Close()
	var result []string
	for rows.Next() {
		var s string
		if err := rows.Scan(&s); err == nil {
			result = append(result, s)
		}
	}
	return result
}

func handleReport(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	parts := strings.SplitN(strings.TrimPrefix(r.URL.Path, "/api/report/"), "/", 3)
	if len(parts) < 2 {
		respErr(w, 400, "invalid path")
		return
	}
	taskID := parts[0]
	format := parts[1]
	TasksMu.RLock()
	t, ok := Tasks[taskID]
	TasksMu.RUnlock()
	if !ok {
		respErr(w, 404, "task not found")
		return
	}
	switch format {
	case "json":
		respJSON(w, t.Result)
	case "csv":
		w.Header().Set("Content-Type", "text/csv")
		w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="scan_%s.csv"`, taskID))
		writeCSV(w, t)
	case "pdf":
		pdfPath, err := generatePDF(t)
		if err != nil {
			respErr(w, 500, "pdf error: "+err.Error())
			return
		}
		http.ServeFile(w, r, pdfPath)
	default:
		respErr(w, 400, "unsupported format")
	}
}

func writeCSV(w io.Writer, t *Task) {
	cw := csv.NewWriter(w)
	cw.Write([]string{"Type", "URL", "Detail", "Master"})
	if t.Result != nil {
		for _, l := range t.Result.BlacklinkList {
			for _, r := range l.Results {
				cw.Write([]string{"Blacklink", l.URL, r, strJoin(l.Master)})
			}
		}
		for _, l := range t.Result.BackdoorList {
			for _, r := range l.Results {
				cw.Write([]string{"Backdoor", l.URL, r, strJoin(l.Master)})
			}
		}
		for _, l := range t.Result.ViolativelinkList {
			for _, r := range l.Results {
				cw.Write([]string{"Violative", l.URL, r, strJoin(l.Master)})
			}
		}
		for _, l := range t.Result.DiedlinkList {
			cw.Write([]string{"DeadLink", l.URL, l.StatusCode, strJoin(l.Master)})
		}
	}
	cw.Flush()
}

func handleCleanup(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	if r.Method != http.MethodPost {
		respErr(w, 405, "method not allowed")
		return
	}
	cutoff := time.Now().AddDate(0, 0, -7)
	TasksMu.Lock()
	deleted := 0
	for id, t := range Tasks {
		if (t.Status == "success" || t.Status == "error" || t.Status == "timeout") && t.FinishedAt.Before(cutoff) {
			delete(Tasks, id)
			deleted++
		}
	}
	TasksMu.Unlock()
	respJSON(w, map[string]interface{}{"deleted": deleted})
}

type aiAnalyzeReq struct {
	Result interface{} `json:"result"`
}

func handleAIAnalyze(w http.ResponseWriter, r *http.Request) {
	setCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(204)
		return
	}
	if r.Method != http.MethodPost {
		respErr(w, 405, "method not allowed")
		return
	}
	var req aiAnalyzeReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respErr(w, 400, "invalid json")
		return
	}

	// Try Ollama first
	ollamaResp, ollamaErr := callOllama(req.Result)
	if ollamaErr == nil && ollamaResp != "" {
		respJSON(w, map[string]interface{}{
			"risk_level": classifyRisk(ollamaResp),
			"analysis":   ollamaResp,
			"source":     "ollama",
			"suggestions": genSuggestions(ollamaResp),
		})
		return
	}

	// Fallback: rule-based analysis
	result := req.Result
	summary := summarizeResult(result)
	respJSON(w, map[string]interface{}{
		"risk_level":  summary.risk,
		"analysis":    summary.text,
		"source":      "rule",
		"suggestions": summary.suggestions,
	})
}

func callOllama(result interface{}) (string, error) {
	jsonData, err := json.Marshal(map[string]interface{}{
		"model":    "qwen2.5:7b",
		"prompt":   fmt.Sprintf("You are a web security expert. Analyze this scan result in Chinese. Output format: [risk level] [brief analysis]. Risk levels: high/medium/low.\nResult:\n%s", mustMarshalJSON(result)),
		"stream":   false,
		"options":  map[string]interface{}{"temperature": 0.3, "num_predict": 512},
	})
	if err != nil {
		return "", err
	}
	resp, err := http.Post("http://localhost:11434/api/generate", "application/json",
		strings.NewReader(string(jsonData)))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("ollama status: %d", resp.StatusCode)
	}
	var out struct {
		Response string `json:"response"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return "", err
	}
	return out.Response, nil
}

type ruleSummary struct {
	risk        string
	text        string
	suggestions []string
}

func summarizeResult(r interface{}) ruleSummary {
	m, ok := r.(map[string]interface{})
	if !ok {
		return ruleSummary{risk: "low", text: "Unable to parse scan result", suggestions: []string{"Please check if scan task completed normally"}}
	}
	var blacks, backdoors, viol int
	if v, ok := m["blacklink_list"].([]interface{}); ok {
		blacks = len(v)
	}
	if v, ok := m["backdoor_list"].([]interface{}); ok {
		backdoors = len(v)
	}
	if v, ok := m["violativelink_list"].([]interface{}); ok {
		viol = len(v)
	}
	var risk string
	var suggestions []string
	if backdoors > 0 {
		risk = "high"
		suggestions = []string{"Immediately isolate infected pages", "Full backdoor scan", "Check server login logs"}
	} else if blacks > 0 {
		risk = "medium"
		suggestions = []string{"Clean blacklink content", "Check external link sources", "Strengthen content review"}
	} else if viol > 0 {
		risk = "low"
		suggestions = []string{"Clean violative links", "Strengthen site content inspection"}
	} else {
		risk = "low"
		suggestions = []string{"Continue regular scan monitoring", "Maintain current security measures"}
	}
	text := fmt.Sprintf("Scan complete. Found %d blacklinks, %d backdoors, %d violative links. Overall risk: %s.",
		blacks, backdoors, viol, risk)
	return ruleSummary{risk: risk, text: text, suggestions: suggestions}
}

func classifyRisk(text string) string {
	lower := strings.ToLower(text)
	if strings.Contains(lower, "high") || strings.Contains(lower, "high risk") || strings.Contains(lower, "severe") {
		return "high"
	}
	if strings.Contains(lower, "medium") || strings.Contains(lower, "warning") {
		return "medium"
	}
	return "low"
}

func genSuggestions(text string) []string {
	lower := strings.ToLower(text)
	var s []string
	if strings.Contains(lower, "backdoor") || strings.Contains(lower, "webshell") {
		s = append(s, "Immediately isolate infected pages", "Full backdoor scan")
	}
	if strings.Contains(lower, "blacklink") {
		s = append(s, "Clean blacklink content", "Check external link sources")
	}
	if strings.Contains(lower, "violative") {
		s = append(s, "Clean violative links", "Strengthen content review")
	}
	if s == nil {
		s = []string{"Continue regular scan monitoring", "Maintain current security measures"}
	}
	return s
}

func mustMarshalJSON(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}

func sanitizeURL(raw string) string {
	raw = strings.TrimSpace(raw)
	raw = strings.TrimPrefix(raw, "https://")
	raw = strings.TrimPrefix(raw, "http://")
	re := regexp.MustCompile(`[;&|$'"<>\\]`)
	raw = re.ReplaceAllString(raw, "")
	if len(raw) > 500 {
		return raw[:500]
	}
	return raw
}

func validScanType(t string) bool {
	switch t {
	case "HomePage_Scan", "SecondPage_Scan", "AllSite_Scan", "CustomPage_Scan":
		return true
	}
	return false
}

func runExternalCmd(name string, args ...string) error {
	return exec.Command(name, args...).Run()
}

