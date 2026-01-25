import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Activity, Users, CreditCard, TrendingUp } from "lucide-react";

export function Dashboard() {
  const stats = [
    { title: "Total Revenue", value: "$45,231", change: "+20.1%", icon: CreditCard },
    { title: "Active Users", value: "2,350", change: "+15.3%", icon: Users },
    { title: "Engagement Rate", value: "68.5%", change: "+5.2%", icon: Activity },
    { title: "Growth", value: "+12.5%", change: "+2.4%", icon: TrendingUp },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1>Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back! Here's an overview of your metrics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">{stat.title}</CardTitle>
              <stat.icon className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-600">{stat.change}</span> from last month
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Your latest updates and changes</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { title: "New user registration", time: "5 minutes ago" },
                { title: "System update completed", time: "1 hour ago" },
                { title: "Payment received", time: "3 hours ago" },
                { title: "New feature deployed", time: "5 hours ago" },
              ].map((activity, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p>{activity.title}</p>
                    <p className="text-sm text-muted-foreground">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks and shortcuts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <button className="w-full rounded-lg border p-3 text-left hover:bg-accent">
                Create New Project
              </button>
              <button className="w-full rounded-lg border p-3 text-left hover:bg-accent">
                Invite Team Member
              </button>
              <button className="w-full rounded-lg border p-3 text-left hover:bg-accent">
                Generate Report
              </button>
              <button className="w-full rounded-lg border p-3 text-left hover:bg-accent">
                View Documentation
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
