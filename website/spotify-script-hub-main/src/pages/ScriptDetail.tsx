import { useParams, Link } from "react-router-dom";
import { scripts } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft, Play, Eye } from "lucide-react";
import { useState } from "react";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/components/ui/use-toast";
import { getSessionToken, runScript } from "@/lib/api";

export default function ScriptDetail() {
  const { scriptId } = useParams();
  const script = scripts.find((s) => s.id === scriptId);
  const [isRunning, setIsRunning] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [lastRunAt, setLastRunAt] = useState<string>("");
  const [lastOutput, setLastOutput] = useState<string>("");
  const [lastError, setLastError] = useState<string>("");
  const runnableScript = scriptId === "vaulted-add" ? "vaulted" : scriptId === "liked-songs-mirror" ? "liked" : undefined;

  if (!script) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-muted-foreground">Script not found.</p>
        <Button variant="outline" asChild>
          <Link to="/scripts">Back to Scripts</Link>
        </Button>
      </div>
    );
  }

  const handleRun = () => {
    if (!runnableScript) {
      toast({
        title: "Not wired yet",
        description: "This script is not connected to backend execution yet.",
      });
      return;
    }

    const token = getSessionToken();
    if (!token) {
      toast({
        title: "Spotify login required",
        description: "Connect Spotify in Settings before running scripts.",
      });
      return;
    }

    setIsRunning(true);
    setLastError("");
    setLastOutput("");
    runScript(runnableScript)
      .then((data) => {
        const text = JSON.stringify(data);
        setLastRunAt(new Date().toISOString());
        setLastOutput(text);
        toast({
          title: "Run completed",
          description: text.length > 180 ? `${text.slice(0, 180)}...` : text,
        });
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to dispatch workflow.";
        setLastRunAt(new Date().toISOString());
        setLastError(msg);
        toast({
          title: "Run failed",
          description: msg,
          variant: "destructive",
        });
      })
      .finally(() => setIsRunning(false));
  };

  return (
    <div className="space-y-6 max-w-3xl animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/scripts">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{script.name}</h1>
          <p className="text-muted-foreground">{script.description}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {script.configFields.map((field) => (
            <div key={field.name} className="space-y-2">
              <Label htmlFor={field.name}>{field.label}</Label>
              {field.type === "text" && (
                <Input
                  id={field.name}
                  placeholder={field.placeholder}
                  defaultValue={field.defaultValue as string}
                />
              )}
              {field.type === "number" && (
                <Input
                  id={field.name}
                  type="number"
                  defaultValue={field.defaultValue as number}
                />
              )}
              {field.type === "select" && (
                <Select defaultValue={field.options?.[0]}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {field.options?.map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              {field.type === "toggle" && (
                <Switch
                  id={field.name}
                  defaultChecked={field.defaultValue as boolean}
                />
              )}
            </div>
          ))}

          <Separator />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch id="dry-run" checked={dryRun} onCheckedChange={setDryRun} />
              <Label htmlFor="dry-run" className="flex items-center gap-1.5">
                <Eye className="h-3.5 w-3.5" /> Dry Run
              </Label>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" disabled={isRunning}>
                Preview Changes
              </Button>
              <Button onClick={handleRun} disabled={isRunning}>
                {isRunning ? (
                  <>Running...</>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-1.5" /> Run Script
                  </>
                )}
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {runnableScript
              ? "Run Script executes via backend API using your connected Spotify account."
              : "This script is UI-only right now; no workflow is connected yet."}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Output</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-background rounded-lg p-4 font-mono text-sm text-muted-foreground border min-h-[120px]">
            {isRunning ? (
              <div className="space-y-1">
                <p>$ Running {script.name}...</p>
                <p className="text-primary">→ Connecting to Spotify API...</p>
                <p className="text-primary">→ Fetching library data...</p>
                <p className="animate-pulse">▌</p>
              </div>
            ) : (lastRunAt || lastOutput || lastError) ? (
              <div className="space-y-1">
                {lastRunAt ? <p className="text-muted-foreground/60">Last run: {new Date(lastRunAt).toLocaleString()}</p> : null}
                {lastError ? <p className="text-destructive">Error: {lastError}</p> : null}
                {lastOutput ? <pre className="whitespace-pre-wrap break-all">{lastOutput}</pre> : null}
              </div>
            ) : (
              <p>No runs yet. Configure and click "Run Script" to get started.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
