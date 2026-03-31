import { format } from "date-fns";
import { Download, FileBox, FileWarning, Loader2, ArrowRight } from "lucide-react";
import { useListBimJobs, getDownloadBimFileUrl } from "@workspace/api-client-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "completed": return <Badge variant="default" className="bg-green-600">Completed</Badge>;
    case "processing": return <Badge variant="secondary" className="animate-pulse">Processing</Badge>;
    case "failed": return <Badge variant="destructive">Failed</Badge>;
    default: return <Badge variant="outline">Pending</Badge>;
  }
}

export default function Jobs() {
  const { data: jobsList, isLoading } = useListBimJobs();

  const handleDownload = (jobId: string) => {
    window.open(getDownloadBimFileUrl(jobId), "_blank");
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "--";
    return `${Math.round(bytes / 1024)} KB`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-mono font-bold tracking-tight mb-2">Job History</h1>
        <p className="text-muted-foreground">Review past generated BIM files and their element extraction summaries.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="font-mono text-lg">Generation Logs</CardTitle>
          <CardDescription>Chronological list of all IFC generation attempts.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-48 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              Loading history...
            </div>
          ) : !jobsList || jobsList.jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center border-2 border-dashed rounded-lg bg-muted/20">
              <FileBox className="h-8 w-8 text-muted-foreground mb-3 opacity-50" />
              <p className="text-muted-foreground font-medium">No jobs found</p>
              <p className="text-sm text-muted-foreground">Your generation history will appear here.</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-mono w-[30%]">Project</TableHead>
                    <TableHead className="font-mono w-[15%]">Date</TableHead>
                    <TableHead className="font-mono w-[15%]">Status</TableHead>
                    <TableHead className="font-mono w-[20%]">Elements Found</TableHead>
                    <TableHead className="font-mono w-[10%]">Size</TableHead>
                    <TableHead className="font-mono w-[10%] text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobsList.jobs.map((job) => {
                    const totalElements = job.extractedElements 
                      ? Object.values(job.extractedElements).reduce((a, b) => (a || 0) + (b || 0), 0)
                      : 0;

                    return (
                      <TableRow key={job.id}>
                        <TableCell className="font-medium">
                          {job.meetingTitle || "Untitled Project"}
                          {job.errorMessage && (
                            <p className="text-xs text-destructive mt-1 font-mono flex items-center">
                              <FileWarning className="h-3 w-3 mr-1" />
                              {job.errorMessage}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                          {format(new Date(job.createdAt), "MMM d, yyyy HH:mm")}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={job.status} />
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-muted-foreground">
                            {job.status === "completed" ? `${totalElements} items` : "--"}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-muted-foreground">
                            {formatFileSize(job.fileSize)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          {job.status === "completed" && (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              onClick={() => handleDownload(job.id)}
                              className="font-mono text-xs"
                            >
                              <Download className="h-3 w-3 mr-1" />
                              IFC
                            </Button>
                          )}
                          {job.status === "failed" && (
                            <Button variant="ghost" size="sm" disabled className="text-xs">
                              Failed
                            </Button>
                          )}
                          {(job.status === "pending" || job.status === "processing") && (
                            <Button variant="ghost" size="sm" disabled className="text-xs">
                              <Loader2 className="h-3 w-3 animate-spin" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
