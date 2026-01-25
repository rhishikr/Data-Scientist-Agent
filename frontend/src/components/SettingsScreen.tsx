import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Switch } from "./ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Separator } from "./ui/separator";

export function SettingsScreen() {
  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and application preferences
        </p>
      </div>

      {/* Pipeline Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Configuration</CardTitle>
          <CardDescription>Configure automated analytics pipeline settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="pipeline-frequency">Run Frequency</Label>
            <Select defaultValue="daily">
              <SelectTrigger id="pipeline-frequency">
                <SelectValue placeholder="Select frequency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hourly">Every Hour</SelectItem>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="manual">Manual Only</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">How often the pipeline should automatically run</p>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="auto-pipeline">Automatic Pipeline Execution</Label>
              <p className="text-sm text-muted-foreground">
                Run pipeline automatically when new data is detected
              </p>
            </div>
            <Switch id="auto-pipeline" defaultChecked />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="notifications">Pipeline Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Send email notifications when pipeline completes or fails
              </p>
            </div>
            <Switch id="notifications" defaultChecked />
          </div>
        </CardContent>
      </Card>

      {/* Data Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Data Settings</CardTitle>
          <CardDescription>Configure data retention and storage</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="retention">Data Retention Period</Label>
            <Select defaultValue="1year">
              <SelectTrigger id="retention">
                <SelectValue placeholder="Select period" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3months">3 Months</SelectItem>
                <SelectItem value="6months">6 Months</SelectItem>
                <SelectItem value="1year">1 Year</SelectItem>
                <SelectItem value="2years">2 Years</SelectItem>
                <SelectItem value="forever">Forever</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">How long to keep historical data</p>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="auto-cleanup">Automatic Data Cleanup</Label>
              <p className="text-sm text-muted-foreground">
                Automatically remove old data based on retention period
              </p>
            </div>
            <Switch id="auto-cleanup" defaultChecked />
          </div>
        </CardContent>
      </Card>

      {/* Model Settings */}
      <Card>
        <CardHeader>
          <CardTitle>ML Model Settings</CardTitle>
          <CardDescription>Configure machine learning model preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model-type">Default Model Type</Label>
            <Select defaultValue="xgboost">
              <SelectTrigger id="model-type">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="xgboost">XGBoost</SelectItem>
                <SelectItem value="random-forest">Random Forest</SelectItem>
                <SelectItem value="neural-network">Neural Network</SelectItem>
                <SelectItem value="auto">Auto-Select</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">Primary algorithm for predictions</p>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label htmlFor="confidence">Confidence Threshold</Label>
            <Input id="confidence" type="number" defaultValue="0.75" step="0.05" min="0" max="1" />
            <p className="text-xs text-muted-foreground">Minimum confidence for predictions (0-1)</p>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="auto-retrain">Automatic Model Retraining</Label>
              <p className="text-sm text-muted-foreground">
                Retrain models when new data improves accuracy
              </p>
            </div>
            <Switch id="auto-retrain" defaultChecked />
          </div>
        </CardContent>
      </Card>

      {/* LLM Settings */}
      <Card>
        <CardHeader>
          <CardTitle>AI Assistant Settings</CardTitle>
          <CardDescription>Configure LLM assistant preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="response-style">Response Style</Label>
            <Select defaultValue="balanced">
              <SelectTrigger id="response-style">
                <SelectValue placeholder="Select style" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="concise">Concise</SelectItem>
                <SelectItem value="balanced">Balanced</SelectItem>
                <SelectItem value="detailed">Detailed</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">How detailed AI responses should be</p>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="show-context">Show Context Tags</Label>
              <p className="text-sm text-muted-foreground">
                Display data context in assistant interface
              </p>
            </div>
            <Switch id="show-context" defaultChecked />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="inline-charts">Inline Charts</Label>
              <p className="text-sm text-muted-foreground">
                Show charts and visualizations in AI responses
              </p>
            </div>
            <Switch id="inline-charts" defaultChecked />
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>Manage alert and notification preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="email-alerts">Email Alerts</Label>
              <p className="text-sm text-muted-foreground">
                Receive email notifications for important events
              </p>
            </div>
            <Switch id="email-alerts" defaultChecked />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="churn-alerts">Churn Risk Alerts</Label>
              <p className="text-sm text-muted-foreground">
                Alert when high-value customers show churn risk
              </p>
            </div>
            <Switch id="churn-alerts" defaultChecked />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="stock-alerts">Stock-Out Alerts</Label>
              <p className="text-sm text-muted-foreground">
                Alert when inventory reaches critical levels
              </p>
            </div>
            <Switch id="stock-alerts" defaultChecked />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button className="bg-teal-600 hover:bg-teal-700">
          Save Settings
        </Button>
      </div>
    </div>
  );
}
