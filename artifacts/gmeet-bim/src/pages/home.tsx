import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { format } from "date-fns";
import { CalendarIcon, Loader2, CheckCircle2, XCircle, ChevronRight, FileDown, Cuboid, Square, DoorOpen, LayoutTemplate, Columns2, Rows, Box } from "lucide-react";

import { useGenerateBim, useGetBimJob, getGetBimJobQueryKey, useListBimJobs, getDownloadBimFileUrl } from "@workspace/api-client-react";

import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const generateSchema = z.object({
  meetingTitle: z.string().optional(),
  meetingDate: z.date().optional(),
  meetingNotes: z.string().min(10, "Please provide comprehensive meeting notes to extract BIM elements."),
});

type GenerateValues = z.infer<typeof generateSchema>;

const iconMap = {
  spaces: Square,
  walls: Rows,
  doors: DoorOpen,
  windows: LayoutTemplate,
  columns: Columns2,
  beams: Rows,
  slabs: Box,
};

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "completed": return <Badge variant="default" className="bg-green-600 hover:bg-green-700">Completed</Badge>;
    case "processing": return <Badge variant="secondary" className="animate-pulse">Processing</Badge>;
    case "failed": return <Badge variant="destructive">Failed</Badge>;
    default: return <Badge variant="outline">Pending</Badge>;
  }
}

export default function Home() {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  
  const generateBim = useGenerateBim();
  
  const form = useForm<GenerateValues>({
    resolver: zodResolver(generateSchema),
    defaultValues: {
      meetingTitle: "",
      meetingNotes: "",
    },
  });

  const { data: jobStatus, isFetching: isPolling } = useGetBimJob(currentJobId || "", {
    query: {
      enabled: !!currentJobId,
      refetchInterval: (query) => {
        const status = query.state.data?.status;
        if (status === "completed" || status === "failed") return false;
        return 2000;
      },
      queryKey: currentJobId ? getGetBimJobQueryKey(currentJobId) : ["null"],
    }
  });

  const { data: recentJobs } = useListBimJobs({
    query: {
      // Only fetch if not currently polling a job to avoid too many requests
      enabled: !currentJobId || (jobStatus?.status === "completed" || jobStatus?.status === "failed"),
    }
  });

  const onSubmit = (data: GenerateValues) => {
    generateBim.mutate({
      data: {
        meetingNotes: data.meetingNotes,
        meetingTitle: data.meetingTitle || "Untitled Meeting",
        meetingDate: data.meetingDate ? data.meetingDate.toISOString() : new Date().toISOString(),
      }
    }, {
      onSuccess: (response) => {
        setCurrentJobId(response.jobId);
      }
    });
  };

  const handleDownload = () => {
    if (!currentJobId) return;
    window.open(getDownloadBimFileUrl(currentJobId), "_blank");
  };

  const activeStepIndex = jobStatus?.steps?.findIndex(s => s.status === "active") ?? -1;

  return (
    <div className="grid gap-8">
      <div>
        <h1 className="text-3xl font-mono font-bold tracking-tight mb-2">IFC Generator</h1>
        <p className="text-muted-foreground text-lg">Extract structural elements and spatial arrangements from meeting notes to generate open-standard BIM models.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-mono text-xl">Generation Parameters</CardTitle>
              <CardDescription>Input the project brief or meeting transcription.</CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="meetingTitle"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Project / Meeting Title</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Design Review - Phase 2" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="meetingDate"
                      render={({ field }) => (
                        <FormItem className="flex flex-col">
                          <FormLabel>Date of Meeting</FormLabel>
                          <Popover>
                            <PopoverTrigger asChild>
                              <FormControl>
                                <Button
                                  variant={"outline"}
                                  className={`w-full pl-3 text-left font-normal ${!field.value && "text-muted-foreground"}`}
                                >
                                  {field.value ? format(field.value, "PPP") : <span>Pick a date</span>}
                                  <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                </Button>
                              </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0" align="start">
                              <Calendar
                                mode="single"
                                selected={field.value}
                                onSelect={field.onChange}
                                disabled={(date) => date > new Date() || date < new Date("1900-01-01")}
                                initialFocus
                              />
                            </PopoverContent>
                          </Popover>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={form.control}
                    name="meetingNotes"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Meeting Notes / Transcription</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="Paste meeting transcript here. Make sure to include mentions of dimensions, materials, spaces, and layout..."
                            className="min-h-[250px] font-mono text-sm resize-y"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Button 
                    type="submit" 
                    className="w-full font-mono text-base" 
                    size="lg"
                    disabled={generateBim.isPending || (jobStatus && (jobStatus.status === "processing" || jobStatus.status === "pending"))}
                  >
                    {generateBim.isPending ? (
                      <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Initializing...</>
                    ) : (
                      <><Cuboid className="mr-2 h-5 w-5" /> Generate BIM File</>
                    )}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-5 space-y-6">
          {jobStatus ? (
            <Card className="border-primary/20 shadow-md">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between mb-2">
                  <CardTitle className="font-mono flex items-center gap-2">
                    <Loader2 className={`h-5 w-5 ${jobStatus.status === 'processing' ? 'animate-spin text-primary' : 'hidden'}`} />
                    Job Status
                  </CardTitle>
                  <StatusBadge status={jobStatus.status} />
                </div>
                <Progress value={jobStatus.progress || 0} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground mt-2 font-mono">
                  <span>{jobStatus.progress || 0}%</span>
                  <span>{jobStatus.currentStep || "Initializing..."}</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  {jobStatus.steps?.map((step, idx) => (
                    <div key={idx} className="flex flex-col gap-1 relative">
                      {idx !== jobStatus.steps!.length - 1 && (
                        <div className="absolute left-[11px] top-[24px] bottom-[-12px] w-[2px] bg-border z-0" />
                      )}
                      <div className="flex items-start gap-3 z-10 bg-card py-1">
                        <div className="mt-0.5">
                          {step.status === "completed" && <CheckCircle2 className="h-5 w-5 text-green-500 fill-green-500/10" />}
                          {step.status === "active" && <Loader2 className="h-5 w-5 text-primary animate-spin" />}
                          {step.status === "failed" && <XCircle className="h-5 w-5 text-destructive" />}
                          {step.status === "pending" && <div className="h-5 w-5 rounded-full border-2 border-muted bg-card" />}
                        </div>
                        <div className="flex-1">
                          <p className={`font-medium text-sm ${step.status === 'pending' ? 'text-muted-foreground' : 'text-foreground'}`}>
                            {step.name}
                          </p>
                          {step.description && (
                            <p className="text-xs text-muted-foreground">{step.description}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {jobStatus.status === "failed" && jobStatus.errorMessage && (
                  <div className="p-3 bg-destructive/10 text-destructive rounded-md text-sm font-mono border border-destructive/20">
                    Error: {jobStatus.errorMessage}
                  </div>
                )}

                {jobStatus.status === "completed" && jobStatus.extractedElements && (
                  <div className="pt-4 border-t">
                    <h4 className="text-sm font-medium mb-3 text-muted-foreground">Extracted Elements</h4>
                    <div className="grid grid-cols-2 gap-3">
                      {Object.entries(jobStatus.extractedElements).map(([key, count]) => {
                        const Icon = iconMap[key as keyof typeof iconMap] || Box;
                        if (!count) return null;
                        return (
                          <div key={key} className="flex items-center justify-between p-2 rounded bg-secondary/50 border border-border/50">
                            <div className="flex items-center gap-2 text-sm capitalize">
                              <Icon className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">{key}</span>
                            </div>
                            <span className="font-mono font-medium">{count}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
              {jobStatus.status === "completed" && (
                <CardFooter className="pt-0">
                  <Button onClick={handleDownload} className="w-full bg-green-600 hover:bg-green-700 text-white font-mono">
                    <FileDown className="mr-2 h-4 w-4" /> Download .IFC Model
                    {jobStatus.fileSize && <span className="ml-2 opacity-70">({Math.round(jobStatus.fileSize / 1024)} KB)</span>}
                  </Button>
                </CardFooter>
              )}
            </Card>
          ) : (
            <Card className="bg-muted/50 border-dashed">
              <CardContent className="flex flex-col items-center justify-center h-[300px] text-center text-muted-foreground">
                <Box className="h-12 w-12 mb-4 opacity-20" />
                <p className="font-medium text-lg">No active generation</p>
                <p className="text-sm mt-1 max-w-[250px]">Submit meeting notes to start extracting elements and generating an IFC file.</p>
              </CardContent>
            </Card>
          )}

          {/* Recent Jobs Preview */}
          {recentJobs && recentJobs.jobs.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-mono font-bold text-muted-foreground tracking-wider uppercase">Recent Outputs</h3>
              </div>
              <div className="grid gap-3">
                {recentJobs.jobs.slice(0, 3).map(job => (
                  <Card key={job.id} className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => setCurrentJobId(job.id)}>
                    <div className="p-4 flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="font-medium text-sm line-clamp-1">{job.meetingTitle || "Untitled"}</p>
                        <p className="text-xs text-muted-foreground font-mono">
                          {job.completedAt ? format(new Date(job.completedAt), "MMM d, HH:mm") : format(new Date(job.createdAt), "MMM d, HH:mm")}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={job.status} />
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
