import { ListMusic, Heart, Users } from "lucide-react";
import { StatCard } from "@/components/StatCard";
import { ScriptCard } from "@/components/ScriptCard";
import { mockUser, scripts } from "@/lib/mock-data";

export default function Dashboard() {
  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Welcome back, {mockUser.displayName}</h1>
        <p className="text-muted-foreground">Here's your Spotify library overview.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Playlists" value={mockUser.playlists} icon={ListMusic} />
        <StatCard label="Saved Tracks" value={mockUser.savedTracks.toLocaleString()} icon={Heart} />
        <StatCard label="Following" value={mockUser.following} icon={Users} />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scripts.map((script) => (
            <ScriptCard key={script.id} script={script} />
          ))}
        </div>
      </div>
    </div>
  );
}
