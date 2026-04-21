package main

import (
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/robfig/cron/v3"
)

var (
	port          = flag.String("port", ":5188", "listen address")
	baseDir       = flag.String("dir", "/opt/Orion", "Orion base directory")
	maxConcurrent = flag.Int("workers", 10, "max concurrent scans")
	serveStatic   = flag.Bool("static", true, "serve built web UI")
)

var sched *cron.Cron

func main() {
	flag.Parse()
	runtime.GOMAXPROCS(runtime.NumCPU())
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	binDir, _ := os.Executable()
	if *baseDir == "/opt/Orion" {
		if filepath.Base(filepath.Dir(binDir)) == "Orion-server" {
			*baseDir = filepath.Dir(filepath.Dir(binDir))
		} else if cwd, err := os.Getwd(); err == nil && filepath.Base(cwd) == "Orion-server" {
			*baseDir = filepath.Dir(cwd)
		}
	}

	log.Printf("[Orion] base_dir=%s bin=%s", *baseDir, binDir)

	if err := os.MkdirAll(filepath.Join(*baseDir, "reports"), 0755); err != nil {
		log.Fatalf("cannot create reports dir: %v", err)
	}

	loadState()
	startWorkerPool(*maxConcurrent)

	sched = cron.New(cron.WithSeconds(), cron.WithLocation(time.Local))
	sched.Start()
	restoreScheduledJobs()
	go schedulerLoop()
	go pendingLoop()
	go startMonitorLoop()

	mux := http.NewServeMux()

	if *serveStatic {
		webRoot := filepath.Join(*baseDir, "Orion-web", "dist")
		if _, err := os.Stat(webRoot); err == nil {
			mux.Handle("/app/", http.StripPrefix("/app/", spaHandler(webRoot)))
			mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(webRoot))))
			mux.Handle("/", spaHandler(webRoot))
			log.Printf("[static] serving from: %s", webRoot)
		} else {
			log.Printf("[static] dist not found at %s, API-only mode", webRoot)
		}
	}

	mux.HandleFunc("/api/health", handleHealth)
	mux.HandleFunc("/api/stats", handleStats)
	mux.HandleFunc("/api/scan", handleScan)
	mux.HandleFunc("/api/scan/", handleScanStatus)
	mux.HandleFunc("/api/tasks", handleTasks)
	mux.HandleFunc("/api/tasks/", handleTaskDelete)
	mux.HandleFunc("/api/batch", handleBatch)
	mux.HandleFunc("/api/batch/", handleBatchStatus)
	mux.HandleFunc("/api/schedule", handleSchedule)
	mux.HandleFunc("/api/schedule/", handleScheduleOp)
	mux.HandleFunc("/api/rules", handleRules)
	mux.HandleFunc("/api/rules/", handleRules)
	mux.HandleFunc("/api/report/", handleReport)
	mux.HandleFunc("/api/cleanup", handleCleanup)
	mux.HandleFunc("/api/assets", handleAssetsProxy)
	mux.HandleFunc("/api/assets/", handleAssetsProxy)
	mux.HandleFunc("/api/site-monitor", handleSiteMonitor)
	mux.HandleFunc("/api/site-monitor/", handleSiteMonitor)
	mux.HandleFunc("/api/threat-summary", handleThreatSummary)
	mux.HandleFunc("/api/tasks/paginated", handleTasksPaginated)

	srv := &http.Server{
		Addr:         *port,
		Handler:      mux,
		ReadTimeout:  60 * time.Second,
		WriteTimeout: 300 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Printf("[Orion] Go API starting on %s | dir=%s | workers=%d", *port, *baseDir, *maxConcurrent)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

func spaHandler(root string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p := r.URL.Path
		// Strip leading slash so filepath.Join works correctly on all OSes
		p = strings.TrimPrefix(p, "/")
		if p == "" {
			p = "index.html"
		}
		fpath := filepath.Join(root, p)

		// Security: ensure the resolved path is inside root
		abs, _ := filepath.Abs(fpath)
		rootAbs, _ := filepath.Abs(root)
		if !strings.HasPrefix(abs, rootAbs) {
			http.Error(w, "not found", 404)
			return
		}

		data, err := os.ReadFile(fpath)
		if err != nil {
			// Fallback: serve index.html for SPA routing
			fpath = filepath.Join(root, "index.html")
			data, err = os.ReadFile(fpath)
			if err != nil {
				http.Error(w, "not found", 404)
				return
			}
			p = "index.html"
		}

		if ct := mimeType(filepath.Ext(p)); ct != "" {
			w.Header().Set("Content-Type", ct)
		}
		if filepath.Ext(p) != ".html" {
			w.Header().Set("Cache-Control", "public, max-age=86400")
		}
		w.Write(data)
	})
}

func mimeType(ext string) string {
	return map[string]string{
		".html": "text/html; charset=utf-8",
		".js":   "application/javascript",
		".mjs":  "application/javascript",
		".css":  "text/css",
		".svg":  "image/svg+xml",
		".png":  "image/png",
		".jpg":  "image/jpeg",
		".jpeg": "image/jpeg",
		".ico":  "image/x-icon",
		".woff2": "font/woff2",
		".woff":  "font/woff",
		".ttf":   "font/ttf",
		".map":   "application/json",
		".json":  "application/json",
		".txt":   "text/plain",
	}[ext]
}

func respJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}

func respErr(w http.ResponseWriter, code int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": msg})
}

func sanitizePath(path string) string {
	return filepath.Base(path)
}