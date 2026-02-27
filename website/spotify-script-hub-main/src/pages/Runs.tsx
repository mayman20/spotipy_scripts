import { mockRuns } from "@/lib/mock-data";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";

const statusStyles: Record<string, string> = {
  queued: "bg-muted text-muted-foreground",
  running: "bg-info/10 text-info",
  succeeded: "bg-primary/10 text-primary",
  failed: "bg-destructive/10 text-destructive",
};

export default function Runs() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Run History</h1>
        <p className="text-muted-foreground">
          Track the status and output of your script executions.
        </p>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Script</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockRuns.map((run) => (
              <TableRow key={run.id}>
                <TableCell className="font-medium">{run.scriptName}</TableCell>
                <TableCell>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusStyles[run.status]}`}
                  >
                    {run.status}
                  </span>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {new Date(run.startedAt).toLocaleString()}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {run.duration}
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" asChild>
                    <Link to={`/scripts/${run.scriptId}`}>
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
