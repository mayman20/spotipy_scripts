import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Star, Heart, Archive, Copy, Lock, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { Script } from "@/lib/types";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Star, Heart, Archive, Copy, Lock, Zap,
};

interface ScriptCardProps {
  script: Script;
  showActions?: boolean;
}

export function ScriptCard({ script, showActions = true }: ScriptCardProps) {
  const Icon = iconMap[script.icon] || Zap;

  return (
    <Card className="group hover:border-primary/30 transition-all duration-300">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <CardTitle className="text-base">{script.name}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <p className="text-sm text-muted-foreground">{script.description}</p>
      </CardContent>
      {showActions && (
        <CardFooter className="gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/scripts/${script.id}`}>Configure</Link>
          </Button>
          <Button size="sm" asChild>
            <Link to={`/scripts/${script.id}`}>Run</Link>
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
