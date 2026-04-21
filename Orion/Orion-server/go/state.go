package main

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

var statePath = filepath.Join(func() string {
	if *baseDir != "" {
		return *baseDir
	}
	ex, _ := os.Executable()
	return filepath.Dir(ex)
}(), "orion_state.json")

type persistedState struct {
	Tasks     []*Task        `json:"tasks"`
	Batches   []*Batch       `json:"batches"`
	SchedJobs []*ScheduleJob `json:"sched_jobs"`
	SavedAt   string         `json:"saved_at"`
}

var saveMu sync.Mutex

func saveState() {
	saveMu.Lock()
	defer saveMu.Unlock()

	TasksMu.RLock()
	tasks := make([]*Task, 0, len(Tasks))
	for _, t := range Tasks {
		tasks = append(tasks, t)
	}
	TasksMu.RUnlock()

	BatchesMu.RLock()
	batches := make([]*Batch, 0, len(Batches))
	for _, b := range Batches {
		batches = append(batches, b)
	}
	BatchesMu.RUnlock()

	SchedMu.RLock()
	jobs := make([]*ScheduleJob, 0, len(SchedJobs))
	for _, j := range SchedJobs {
		jobs = append(jobs, j)
	}
	SchedMu.RUnlock()

	sf := persistedState{
		Tasks: tasks, Batches: batches, SchedJobs: jobs,
		SavedAt: time.Now().Format(time.RFC3339),
	}
	data, err := json.MarshalIndent(sf, "", "  ")
	if err != nil {
		return
	}
	tmp := statePath + ".tmp"
	if err := os.WriteFile(tmp, data, 0644); err != nil {
		log.Printf("[state] write error: %v", err)
		return
	}
	os.Rename(tmp, statePath)
}

func loadState() {
	data, err := os.ReadFile(statePath)
	if err != nil {
		return
	}
	var sf persistedState
	if err := json.Unmarshal(data, &sf); err != nil {
		log.Printf("[state] parse error: %v", err)
		return
	}
	TasksMu.Lock()
	for _, t := range sf.Tasks {
		Tasks[t.ID] = t
	}
	TasksMu.Unlock()
	BatchesMu.Lock()
	for _, b := range sf.Batches {
		Batches[b.ID] = b
	}
	BatchesMu.Unlock()
	log.Printf("[state] loaded %d tasks, %d batches, %d schedule jobs",
		len(sf.Tasks), len(sf.Batches), len(sf.SchedJobs))
}

func restoreScheduledJobs() {
	SchedMu.RLock()
	defer SchedMu.RUnlock()
	for _, job := range SchedJobs {
		if !job.Enabled {
			continue
		}
		entryID, err := sched.AddFunc(job.CronExpr, func() {
			runScheduledScan(job.URL, job.ScanType)
		})
		if err != nil {
			log.Printf("[scheduler] restore job %s failed: %v", job.ID, err)
			continue
		}
		job.CronEntryID = entryID
		if entry := sched.Entry(entryID); entry.ID != 0 {
			job.NextRun = entry.Next.Format(time.RFC3339)
		}
	}
	log.Printf("[scheduler] restored %d jobs", len(SchedJobs))
}

func schedulerLoop() {
	ticker := time.NewTicker(60 * time.Second)
	for range ticker.C {
		SchedMu.RLock()
		for _, job := range SchedJobs {
			if !job.Enabled || job.CronEntryID == 0 {
				continue
			}
			if entry := sched.Entry(job.CronEntryID); entry.ID != 0 {
				job.NextRun = entry.Next.Format(time.RFC3339)
			}
		}
		SchedMu.RUnlock()
	}
}

func pendingLoop() {
	ticker := time.NewTicker(2 * time.Minute)
	for range ticker.C {
		TasksMu.Lock()
		now := time.Now()
		for id, t := range Tasks {
			if t.Status == "pending" && now.Sub(t.CreatedAt) > 5*time.Minute {
				go submitScan(id, t.URL, t.ScanType)
				log.Printf("[pending] re-submitted stuck task %s", id)
			}
		}
		TasksMu.Unlock()
	}
}