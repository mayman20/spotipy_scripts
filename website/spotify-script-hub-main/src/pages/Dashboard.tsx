import { ScriptCard } from "@/components/ScriptCard";
import { scripts } from "@/lib/mock-data";
import { useCurrentUser } from "@/hooks/use-current-user";

export default function Dashboard() {
  const { user } = useCurrentUser();

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">
          {user ? `Welcome back, ${user.display_name}` : "Welcome"}
        </h1>
        <p className="text-muted-foreground">
          {user
            ? "Run your Spotify automations below."
            : "Connect your Spotify account in Settings to run automations."}
        </p>
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
