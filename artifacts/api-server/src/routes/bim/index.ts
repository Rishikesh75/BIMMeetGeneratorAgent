import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { bimJobsTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";
import {
  extractBimElementsFromNotes,
  generateIfcFile,
} from "./ifc-generator.js";

const router: IRouter = Router();

router.post("/generate", async (req, res) => {
  try {
    const { meetingNotes, meetingTitle, meetingDate } = req.body as {
      meetingNotes: string;
      meetingTitle?: string;
      meetingDate?: string;
    };

    if (!meetingNotes || meetingNotes.trim().length === 0) {
      res.status(400).json({ error: "BAD_REQUEST", message: "meetingNotes is required" });
      return;
    }

    const jobId = randomUUID();
    const initialSteps = [
      { name: "Parsing Notes", status: "pending", description: "Reading and parsing meeting notes" },
      { name: "Extracting Elements", status: "pending", description: "Identifying building elements using AI" },
      { name: "Generating IFC Schema", status: "pending", description: "Building the IFC structure" },
      { name: "Writing IFC File", status: "pending", description: "Encoding and finalizing the IFC file" },
    ];

    await db.insert(bimJobsTable).values({
      id: jobId,
      meetingTitle: meetingTitle || null,
      meetingDate: meetingDate || null,
      meetingNotes: meetingNotes.trim(),
      status: "pending",
      progress: 0,
      currentStep: "Queued",
      steps: initialSteps,
    });

    res.json({ jobId, status: "pending", message: "BIM generation job created" });

    processJob(jobId, meetingNotes, meetingTitle, meetingDate).catch((err) => {
      req.log?.error({ err, jobId }, "BIM job processing failed");
    });
  } catch (err) {
    req.log?.error({ err }, "Failed to create BIM job");
    res.status(500).json({ error: "INTERNAL_ERROR", message: "Failed to create job" });
  }
});

router.get("/jobs", async (req, res) => {
  try {
    const jobs = await db
      .select()
      .from(bimJobsTable)
      .orderBy(bimJobsTable.createdAt);

    const jobList = jobs.reverse().map((job) => ({
      id: job.id,
      meetingTitle: job.meetingTitle,
      meetingDate: job.meetingDate,
      status: job.status,
      progress: job.progress,
      currentStep: job.currentStep,
      steps: job.steps,
      errorMessage: job.errorMessage,
      createdAt: job.createdAt?.toISOString(),
      completedAt: job.completedAt?.toISOString(),
      fileSize: job.fileSize,
      extractedElements: job.extractedElements,
    }));

    res.json({ jobs: jobList });
  } catch (err) {
    req.log?.error({ err }, "Failed to list BIM jobs");
    res.status(500).json({ error: "INTERNAL_ERROR", message: "Failed to fetch jobs" });
  }
});

router.get("/jobs/:jobId", async (req, res) => {
  try {
    const { jobId } = req.params;
    const [job] = await db
      .select()
      .from(bimJobsTable)
      .where(eq(bimJobsTable.id, jobId));

    if (!job) {
      res.status(404).json({ error: "NOT_FOUND", message: "Job not found" });
      return;
    }

    res.json({
      id: job.id,
      meetingTitle: job.meetingTitle,
      meetingDate: job.meetingDate,
      status: job.status,
      progress: job.progress,
      currentStep: job.currentStep,
      steps: job.steps,
      errorMessage: job.errorMessage,
      createdAt: job.createdAt?.toISOString(),
      completedAt: job.completedAt?.toISOString(),
      fileSize: job.fileSize,
      extractedElements: job.extractedElements,
    });
  } catch (err) {
    req.log?.error({ err }, "Failed to get BIM job");
    res.status(500).json({ error: "INTERNAL_ERROR", message: "Failed to fetch job" });
  }
});

router.get("/jobs/:jobId/download", async (req, res) => {
  try {
    const { jobId } = req.params;
    const [job] = await db
      .select()
      .from(bimJobsTable)
      .where(eq(bimJobsTable.id, jobId));

    if (!job) {
      res.status(404).json({ error: "NOT_FOUND", message: "Job not found" });
      return;
    }

    if (job.status !== "completed" || !job.ifcContent) {
      res.status(404).json({ error: "NOT_READY", message: "IFC file not ready" });
      return;
    }

    const filename = `${(job.meetingTitle || "meeting").replace(/[^a-z0-9]/gi, "_")}_${jobId.slice(0, 8)}.ifc`;
    res.setHeader("Content-Type", "application/octet-stream");
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
    res.send(job.ifcContent);
  } catch (err) {
    req.log?.error({ err }, "Failed to download BIM file");
    res.status(500).json({ error: "INTERNAL_ERROR", message: "Failed to download file" });
  }
});

async function processJob(
  jobId: string,
  meetingNotes: string,
  meetingTitle?: string,
  meetingDate?: string,
): Promise<void> {
  const updateStep = async (
    stepIndex: number,
    progress: number,
    currentStep: string,
    steps: { name: string; status: string; description: string }[],
  ) => {
    await db
      .update(bimJobsTable)
      .set({ status: "processing", progress, currentStep, steps })
      .where(eq(bimJobsTable.id, jobId));
  };

  try {
    const steps = [
      { name: "Parsing Notes", status: "active", description: "Reading and parsing meeting notes" },
      { name: "Extracting Elements", status: "pending", description: "Identifying building elements using AI" },
      { name: "Generating IFC Schema", status: "pending", description: "Building the IFC structure" },
      { name: "Writing IFC File", status: "pending", description: "Encoding and finalizing the IFC file" },
    ];

    await updateStep(0, 10, "Parsing Notes", steps);

    await new Promise((r) => setTimeout(r, 500));

    steps[0].status = "completed";
    steps[1].status = "active";
    await updateStep(1, 30, "Extracting Elements", steps);

    const elements = await extractBimElementsFromNotes(meetingNotes, meetingTitle);

    steps[1].status = "completed";
    steps[2].status = "active";
    await updateStep(2, 60, "Generating IFC Schema", steps);

    await new Promise((r) => setTimeout(r, 300));

    steps[2].status = "completed";
    steps[3].status = "active";
    await updateStep(3, 80, "Writing IFC File", steps);

    const ifcContent = generateIfcFile(elements, meetingTitle, meetingDate);

    steps[3].status = "completed";

    const extractedElements = {
      spaces: elements.spaces.length,
      walls: elements.walls.length,
      doors: elements.doors.length,
      windows: elements.windows.length,
      columns: elements.columns.length,
      beams: elements.beams.length,
      slabs: elements.slabs.length,
    };

    await db
      .update(bimJobsTable)
      .set({
        status: "completed",
        progress: 100,
        currentStep: "Done",
        steps,
        ifcContent,
        fileSize: Buffer.byteLength(ifcContent, "utf8"),
        extractedElements,
        completedAt: new Date(),
      })
      .where(eq(bimJobsTable.id, jobId));
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : "Unknown error";
    await db
      .update(bimJobsTable)
      .set({
        status: "failed",
        errorMessage,
        currentStep: "Failed",
      })
      .where(eq(bimJobsTable.id, jobId));
    throw err;
  }
}

export default router;
