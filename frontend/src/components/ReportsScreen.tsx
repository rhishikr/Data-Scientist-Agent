import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog";
import { FileText, Download, Calendar, FileBarChart } from "lucide-react";

export function ReportsScreen() {
  const [selectedSections, setSelectedSections] = useState<string[]>([
    "customer-segments",
    "churn-analysis",
    "sales-forecast",
  ]);

  const reportSections = [
    { id: "customer-segments", label: "Customer Segments", description: "Detailed customer segmentation analysis" },
    { id: "churn-analysis", label: "Churn Analysis", description: "Customer retention and churn risk assessment" },
    { id: "sales-forecast", label: "Sales Forecast", description: "30-day sales predictions and trends" },
    { id: "inventory-risk", label: "Inventory Risk Summary", description: "Stock-out risk and reorder recommendations" },
    { id: "recommended-actions", label: "Recommended Actions", description: "AI-generated action items and insights" },
  ];

  const toggleSection = (id: string) => {
    setSelectedSections((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const recentReports = [
    { name: "Customer Analytics Report - March 2025", date: "2025-03-15", type: "PDF", status: "Ready" },
    { name: "Inventory Forecast - Q1 2025", date: "2025-03-10", type: "PowerPoint", status: "Ready" },
    { name: "Sales Performance Summary", date: "2025-03-05", type: "PDF", status: "Ready" },
    { name: "Weekly Insights Report", date: "2025-02-28", type: "CSV", status: "Ready" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="mb-2">Reports</h1>
          <p className="text-muted-foreground">
            Generate and export analytics reports
          </p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button className="bg-teal-600 hover:bg-teal-700">
              <FileBarChart className="size-4 mr-2" />
              Generate New Report
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Generate Analytics Report</DialogTitle>
              <DialogDescription>
                Select the sections to include in your report
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              {/* Report Sections */}
              <div className="space-y-3">
                <Label>Include in Report</Label>
                {reportSections.map((section) => (
                  <div key={section.id} className="flex items-start space-x-3 p-3 rounded-lg border hover:bg-slate-50">
                    <Checkbox
                      id={section.id}
                      checked={selectedSections.includes(section.id)}
                      onCheckedChange={() => toggleSection(section.id)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <Label htmlFor={section.id} className="cursor-pointer">
                        {section.label}
                      </Label>
                      <p className="text-sm text-muted-foreground">{section.description}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Format Options */}
              <div className="space-y-3">
                <Label>Export Format</Label>
                <div className="grid grid-cols-3 gap-3">
                  <button className="p-4 rounded-lg border border-teal-200 bg-teal-50 hover:bg-teal-100 transition-colors">
                    <FileText className="size-6 text-teal-600 mx-auto mb-2" />
                    <p className="text-sm">PDF</p>
                  </button>
                  <button className="p-4 rounded-lg border hover:border-teal-200 hover:bg-slate-50 transition-colors">
                    <FileBarChart className="size-6 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm">PowerPoint</p>
                  </button>
                  <button className="p-4 rounded-lg border hover:border-teal-200 hover:bg-slate-50 transition-colors">
                    <FileText className="size-6 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm">CSV Summary</p>
                  </button>
                </div>
              </div>

              {/* Preview */}
              <div className="space-y-3">
                <Label>Report Preview</Label>
                <div className="rounded-lg border p-4 bg-slate-50">
                  <div className="aspect-[8.5/11] bg-white rounded shadow-sm flex items-center justify-center">
                    <div className="text-center space-y-2">
                      <FileText className="size-12 text-slate-300 mx-auto" />
                      <div className="space-y-1">
                        <p className="text-sm">Analytics Report</p>
                        <p className="text-xs text-muted-foreground">Demo Store • {new Date().toLocaleDateString()}</p>
                        <p className="text-xs text-muted-foreground">{selectedSections.length} sections included</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3">
                <Button variant="outline">Cancel</Button>
                <Button className="bg-teal-600 hover:bg-teal-700">
                  <Download className="size-4 mr-2" />
                  Generate Report
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Reports Generated</CardTitle>
            <FileText className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">24</div>
            <p className="text-xs text-muted-foreground">
              This month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Most Popular</CardTitle>
            <FileBarChart className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">Customer</div>
            <p className="text-xs text-muted-foreground">
              Analytics reports
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Last Generated</CardTitle>
            <Calendar className="size-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">2 days</div>
            <p className="text-xs text-muted-foreground">
              Ago
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Reports */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Reports</CardTitle>
          <CardDescription>Previously generated analytics reports</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentReports.map((report, index) => (
              <div key={index} className="flex items-center gap-4 p-4 rounded-lg border hover:bg-slate-50">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-teal-50">
                  <FileText className="size-6 text-teal-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{report.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Generated on {report.date} • {report.type}
                  </p>
                </div>
                <Badge variant="outline" className="text-green-600 border-green-200">
                  {report.status}
                </Badge>
                <Button variant="outline" size="sm">
                  <Download className="size-4 mr-2" />
                  Download
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Scheduled Reports */}
      <Card>
        <CardHeader>
          <CardTitle>Scheduled Reports</CardTitle>
          <CardDescription>Automatically generated reports</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center gap-4 p-4 rounded-lg border">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-blue-50">
                <Calendar className="size-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm">Weekly Customer Insights</p>
                <p className="text-xs text-muted-foreground">Every Monday at 9:00 AM</p>
              </div>
              <Badge variant="outline" className="text-blue-600 border-blue-200">Active</Badge>
              <Button variant="ghost" size="sm">Edit</Button>
            </div>
            
            <div className="flex items-center gap-4 p-4 rounded-lg border">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-purple-50">
                <Calendar className="size-6 text-purple-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm">Monthly Performance Summary</p>
                <p className="text-xs text-muted-foreground">First day of each month</p>
              </div>
              <Badge variant="outline" className="text-purple-600 border-purple-200">Active</Badge>
              <Button variant="ghost" size="sm">Edit</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
