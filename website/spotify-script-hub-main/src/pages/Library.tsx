import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ExternalLink, RefreshCw } from "lucide-react";
import { fetchPlaylistFreshness, runArchiveStale } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

type FreshPlaylist = {
  id: string;
  name: string;
  description: string;
  track_count: number;
  last_added_at: string | null;
  days_since_activity: number;
  freshness_score: number;
  spotify_url: string;
  is_vaulted_tagged: boolean;
  is_liked_tagged: boolean;
};

function freshnessStyle(score: number) {
  const clamped = Math.max(0, Math.min(score, 100));
  const red = Math.round(220 - clamped * 1.6);
  const green = Math.round(60 + clamped * 1.4);
  return {
    backgroundColor: `rgba(${red}, ${green}, 90, 0.18)`,
    borderColor: `rgba(${red}, ${green}, 90, 0.45)`,
  };
}

export default function Library() {
  const [playlists, setPlaylists] = useState<FreshPlaylist[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [threshold, setThreshold] = useState("30");
  const [prefix, setPrefix] = useState("[Archive]");
  const [archiving, setArchiving] = useState(false);

  function load() {
    setLoading(true);
    setError("");
    fetchPlaylistFreshness()
      .then((resp) => setPlaylists(resp.data.playlists || []))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load playlist freshness.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  const staleCount = useMemo(() => {
    const t = Number(threshold);
    if (Number.isNaN(t)) return 0;
    return playlists.filter((p) => p.freshness_score <= t).length;
  }, [playlists, threshold]);

  function handleArchive() {
    const t = Number(threshold);
    if (Number.isNaN(t) || t < 0 || t > 100) {
      toast({ title: "Invalid threshold", description: "Use a value between 0 and 100.", variant: "destructive" });
      return;
    }
    setArchiving(true);
    runArchiveStale(t, prefix || "[Archive]")
      .then((resp) => {
        toast({
          title: "Archive run complete",
          description: `Archived ${resp.result.archived_count} playlists.`,
        });
        load();
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Archive run failed.";
        toast({ title: "Archive failed", description: msg, variant: "destructive" });
      })
      .finally(() => setArchiving(false));
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Library Freshness</h1>
          <p className="text-sm text-muted-foreground">
            Playlist activity scored from fresh (100) to stale (0) using last-added track time.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Archive By Freshness Score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Archive playlists with score ≤</p>
              <Input value={threshold} onChange={(e) => setThreshold(e.target.value)} placeholder="30" />
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Archive prefix</p>
              <Input value={prefix} onChange={(e) => setPrefix(e.target.value)} placeholder="[Archive]" />
            </div>
            <div className="flex items-end">
              <Button onClick={handleArchive} disabled={archiving || loading} className="w-full sm:w-auto">
                {archiving ? "Running..." : `Archive ${staleCount} Playlist(s)`}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Playlists</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? <p className="text-sm text-muted-foreground">Loading playlists...</p> : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {!loading && !error && playlists.length === 0 ? (
            <p className="text-sm text-muted-foreground">No playlists found.</p>
          ) : null}
          {!loading && !error && playlists.map((pl) => (
            <div key={pl.id} className="rounded-md border p-3" style={freshnessStyle(pl.freshness_score)}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold truncate">{pl.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {pl.track_count} tracks · Last active {pl.days_since_activity > 900 ? "unknown" : `${pl.days_since_activity}d ago`}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Score: <span className="font-semibold text-foreground">{pl.freshness_score}</span>
                    {pl.is_vaulted_tagged ? " · Vaulted" : ""}
                    {pl.is_liked_tagged ? " · Liked Mirror" : ""}
                  </p>
                </div>
                <a
                  href={pl.spotify_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-primary inline-flex items-center gap-1 whitespace-nowrap"
                >
                  Open
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

