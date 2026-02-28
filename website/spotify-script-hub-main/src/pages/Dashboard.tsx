import { useEffect, useMemo, useState } from "react";
import { ScriptCard } from "@/components/ScriptCard";
import { scripts } from "@/lib/mock-data";
import { useCurrentUser } from "@/hooks/use-current-user";
import { fetchOverviewStats, TimeRange } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Disc3, Heart, ListMusic, Plus } from "lucide-react";

type Overview = {
  time_range: TimeRange;
  counts: {
    playlists_total: number;
    playlists_owned: number;
    saved_tracks_total: number;
    added_7d: number;
    added_30d: number;
  };
  top_artists: Array<{
    id: string;
    name: string;
    genres: string[];
    popularity: number;
    image_url: string | null;
  }>;
  top_tracks: Array<{
    id: string;
    name: string;
    artists: string[];
    popularity: number;
    image_url: string | null;
  }>;
};

const ranges: Array<{ value: TimeRange; label: string }> = [
  { value: "short_term", label: "4 Weeks" },
  { value: "medium_term", label: "6 Months" },
  { value: "long_term", label: "1 Year" },
];

export default function Dashboard() {
  const { user } = useCurrentUser();
  const [timeRange, setTimeRange] = useState<TimeRange>("short_term");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) {
      setOverview(null);
      return;
    }
    setLoading(true);
    setError("");
    fetchOverviewStats(timeRange)
      .then((resp) => setOverview(resp.overview))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load stats.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [timeRange, user]);

  const visibleScripts = useMemo(() => scripts, []);

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">
            {user ? `Welcome back, ${user.display_name}` : "Welcome"}
          </h1>
          <p className="text-muted-foreground">
            {user
              ? "Quick stats from your Spotify account."
              : "Connect your Spotify account in Settings to load dashboard stats."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {ranges.map((r) => (
            <Button
              key={r.value}
              size="sm"
              variant={timeRange === r.value ? "default" : "outline"}
              onClick={() => setTimeRange(r.value)}
            >
              {r.label}
            </Button>
          ))}
        </div>
      </div>

      {user ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Saved Tracks</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-3">
                <Heart className="h-5 w-5 text-primary" />
                <span className="text-2xl font-bold">{overview?.counts.saved_tracks_total ?? "—"}</span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Playlists (Owned)</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-3">
                <ListMusic className="h-5 w-5 text-primary" />
                <span className="text-2xl font-bold">{overview?.counts.playlists_owned ?? "—"}</span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Added Last 7 Days</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-3">
                <Plus className="h-5 w-5 text-primary" />
                <span className="text-2xl font-bold">{overview?.counts.added_7d ?? "—"}</span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Added Last 30 Days</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-3">
                <Disc3 className="h-5 w-5 text-primary" />
                <span className="text-2xl font-bold">{overview?.counts.added_30d ?? "—"}</span>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Artists</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {loading ? <p className="text-sm text-muted-foreground">Loading...</p> : null}
                {!loading && overview?.top_artists?.length ? (
                  overview.top_artists.slice(0, 5).map((artist, idx) => (
                    <div key={artist.id || artist.name} className="flex items-center gap-3">
                      <span className="w-5 text-xs text-muted-foreground">{idx + 1}</span>
                      {artist.image_url ? (
                        <img src={artist.image_url} alt={artist.name} className="h-8 w-8 rounded object-cover" />
                      ) : (
                        <div className="h-8 w-8 rounded bg-muted" />
                      )}
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{artist.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {artist.genres?.slice(0, 2).join(", ") || "No genres"}
                        </p>
                      </div>
                    </div>
                  ))
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Tracks</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {loading ? <p className="text-sm text-muted-foreground">Loading...</p> : null}
                {!loading && overview?.top_tracks?.length ? (
                  overview.top_tracks.slice(0, 5).map((track, idx) => (
                    <div key={track.id || track.name} className="flex items-center gap-3">
                      <span className="w-5 text-xs text-muted-foreground">{idx + 1}</span>
                      {track.image_url ? (
                        <img src={track.image_url} alt={track.name} className="h-8 w-8 rounded object-cover" />
                      ) : (
                        <div className="h-8 w-8 rounded bg-muted" />
                      )}
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{track.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{track.artists?.join(", ")}</p>
                      </div>
                    </div>
                  ))
                ) : null}
              </CardContent>
            </Card>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </>
      ) : null}

      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleScripts.map((script) => (
            <ScriptCard key={script.id} script={script} />
          ))}
        </div>
      </div>
    </div>
  );
}
