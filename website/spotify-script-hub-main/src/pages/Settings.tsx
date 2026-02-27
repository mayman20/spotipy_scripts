import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { LogOut, Shield, Info } from "lucide-react";
import { mockUser } from "@/lib/mock-data";

export default function Settings() {
  return (
    <div className="space-y-6 max-w-2xl animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your connection and preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" /> Spotify Connection
          </CardTitle>
          <CardDescription>Connected as {mockUser.displayName}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Access Token</p>
              <p className="text-xs text-muted-foreground font-mono">••••••••••••••••</p>
            </div>
            <Badge variant="outline" className="text-primary border-primary/30">
              Active
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Refresh Token</p>
              <p className="text-xs text-muted-foreground font-mono">••••••••••••••••</p>
            </div>
            <Badge variant="outline" className="text-primary border-primary/30">
              Stored
            </Badge>
          </div>
          <Separator />
          <Button variant="destructive" className="w-full">
            <LogOut className="h-4 w-4 mr-2" /> Disconnect Spotify
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4" /> About
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <div className="flex justify-between">
            <span>App Version</span>
            <span className="font-mono">1.0.0</span>
          </div>
          <div className="flex justify-between">
            <span>Build</span>
            <span className="font-mono">2026.02.27</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
