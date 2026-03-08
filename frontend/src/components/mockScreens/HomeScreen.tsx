import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  Database,
  GitBranch,
  Users,
  Package,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
} from "lucide-react";

export function HomeScreen() {
  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div>
        <h1 className="mb-2">Welcome to AI Data Scientist Agent</h1>
        <p className="text-muted-foreground">
          Your automated analytics and ML platform for retail & e-commerce
          intelligence
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Data Sources</CardTitle>
            <Database className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">3 Active</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-teal-600">+1 new</span> this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Pipeline Status</CardTitle>
            <GitBranch className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">Running</div>
            <p className="text-xs text-muted-foreground">
              Last run: 2 hours ago
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Active Customers</CardTitle>
            <Users className="size-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">8,347</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+12.5%</span> vs last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Stock-Out Risk</CardTitle>
            <Package className="size-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">23 SKUs</div>
            <p className="text-xs text-muted-foreground">Requires attention</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Pipeline Runs</CardTitle>
            <CardDescription>Automated analytics workflows</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-green-50">
                  <CheckCircle2 className="size-5 text-green-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">Customer Churn Analysis</p>
                  <p className="text-xs text-muted-foreground">
                    Completed • 2 hours ago
                  </p>
                </div>
                <Badge color="green">Success</Badge>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-50">
                  <Clock className="size-5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">Sales Forecast - Next 30 Days</p>
                  <p className="text-xs text-muted-foreground">
                    Running • 45% complete
                  </p>
                </div>
                <Badge color="blue">In Progress</Badge>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-green-50">
                  <CheckCircle2 className="size-5 text-green-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">Inventory Optimization</p>
                  <p className="text-xs text-muted-foreground">
                    Completed • 5 hours ago
                  </p>
                </div>
                <Badge color="green">Success</Badge>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-orange-50">
                  <AlertCircle className="size-5 text-orange-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">Customer Segmentation</p>
                  <p className="text-xs text-muted-foreground">
                    Warning • 1 day ago
                  </p>
                </div>
                <Badge color="orange">Needs Review</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Key Insights & Recommendations</CardTitle>
            <CardDescription>AI-generated action items</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
                <div className="flex items-start gap-3">
                  <TrendingUp className="size-5 text-teal-600 mt-0.5" />
                  <div>
                    <p className="text-sm">High Churn Risk Detected</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      234 customers show high churn probability. Consider
                      targeted re-engagement campaign.
                    </p>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 mt-2 text-teal-700"
                    >
                      View Details →
                    </Button>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
                <div className="flex items-start gap-3">
                  <Package className="size-5 text-orange-600 mt-0.5" />
                  <div>
                    <p className="text-sm">Stock-Out Risk Alert</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      23 SKUs predicted to run out in next 7 days. Reorder
                      recommendations ready.
                    </p>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 mt-2 text-orange-700"
                    >
                      View Forecast →
                    </Button>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
                <div className="flex items-start gap-3">
                  <Users className="size-5 text-purple-600 mt-0.5" />
                  <div>
                    <p className="text-sm">New Customer Segment Identified</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      "Weekend Browsers" segment shows 3.2x higher conversion
                      with evening promotions.
                    </p>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 mt-2 text-purple-700"
                    >
                      Explore Segment →
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks and workflows</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Button
              variant="outline"
              className="justify-start gap-2 h-auto py-3"
            >
              <Database className="size-4" />
              <span>Upload New Data</span>
            </Button>
            <Button
              variant="outline"
              className="justify-start gap-2 h-auto py-3"
            >
              <GitBranch className="size-4" />
              <span>Run Pipeline</span>
            </Button>
            <Button
              variant="outline"
              className="justify-start gap-2 h-auto py-3"
            >
              <Users className="size-4" />
              <span>View Customer Insights</span>
            </Button>
            <Button
              variant="outline"
              className="justify-start gap-2 h-auto py-3"
            >
              <Package className="size-4" />
              <span>Check Inventory</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
