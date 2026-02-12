import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const lineData = [
  { name: "Jan", users: 400, revenue: 2400 },
  { name: "Feb", users: 300, revenue: 1398 },
  { name: "Mar", users: 600, revenue: 9800 },
  { name: "Apr", users: 800, revenue: 3908 },
  { name: "May", users: 700, revenue: 4800 },
  { name: "Jun", users: 900, revenue: 3800 },
];

const barData = [
  { name: "Mon", visits: 4000 },
  { name: "Tue", visits: 3000 },
  { name: "Wed", visits: 2000 },
  { name: "Thu", visits: 2780 },
  { name: "Fri", visits: 1890 },
  { name: "Sat", visits: 2390 },
  { name: "Sun", visits: 3490 },
];

const pieData = [
  { name: "Desktop", value: 400 },
  { name: "Mobile", value: 300 },
  { name: "Tablet", value: 200 },
  { name: "Other", value: 100 },
];

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042"];

export function Analytics() {
  return (
    <div className="space-y-6">
      <div>
        <h1>Analytics and Charts</h1>
        <p className="text-muted-foreground">
          Visualize your data with interactive charts and analytics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>User Growth & Revenue</CardTitle>
            <CardDescription>
              Monthly trends over the last 6 months
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="users"
                  stroke="#8884d8"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="#82ca9d"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Weekly Visits</CardTitle>
            <CardDescription>
              Daily visit statistics for the current week
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="visits" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Device Distribution</CardTitle>
            <CardDescription>Traffic breakdown by device type</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.name}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Key Metrics</CardTitle>
            <CardDescription>Performance indicators summary</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Conversion Rate</span>
                <span className="text-green-600">3.2%</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Bounce Rate</span>
                <span className="text-red-600">42.8%</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Avg Session Duration</span>
                <span>4m 32s</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Page Views</span>
                <span>234,567</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Active Users</span>
                <span>12,345</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
