import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import {
  Upload,
  Database,
  Cloud,
  CheckCircle2,
  AlertCircle,
  FileText,
} from "lucide-react";

export function DataSourcesScreen() {
  const [uploadedFiles] = useState([
    {
      name: "customers.csv",
      status: "validated",
      rows: 8347,
      date: "2025-01-15",
    },
    {
      name: "orders.csv",
      status: "validated",
      rows: 45231,
      date: "2025-01-15",
    },
    {
      name: "inventory.csv",
      status: "mapping",
      rows: 1523,
      date: "2025-01-15",
    },
  ]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="mb-2">Data Sources</h1>
        <p className="text-muted-foreground">
          Connect and manage your data sources for automated analytics
        </p>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="upload" className="space-y-6">
        <TabsList>
          <TabsTrigger value="upload">Upload CSV/Excel</TabsTrigger>
          <TabsTrigger value="cloud">Cloud / Data Warehouse</TabsTrigger>
          <TabsTrigger value="sql">SQL Database</TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Upload Area - 2 columns */}
            <div className="lg:col-span-2 space-y-6">
              {/* Drag & Drop Card */}
              <Card className="border-2 border-dashed border-teal-200 bg-teal-50/50">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <div className="flex size-16 items-center justify-center rounded-full bg-teal-100 mb-4">
                    <Upload className="size-8 text-teal-600" />
                  </div>
                  <h3 className="mb-2">Upload Data Files</h3>
                  <p className="text-sm text-muted-foreground text-center mb-4 max-w-md">
                    Drag and drop your CSV or Excel files here, or click to
                    browse. Files will be automatically validated and mapped.
                  </p>
                  <Button className="bg-teal-600 hover:bg-teal-700">
                    <Upload className="size-4 mr-2" />
                    Choose Files
                  </Button>
                  <p className="text-xs text-muted-foreground mt-4">
                    Supported formats: CSV, XLSX, XLS (Max 500MB)
                  </p>
                </CardContent>
              </Card>

              {/* Uploaded Files List */}
              <Card>
                <CardHeader>
                  <CardTitle>Uploaded Files</CardTitle>
                  <CardDescription>Recently uploaded datasets</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {uploadedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-4 p-3 rounded-md border bg-white hover:bg-slate-50"
                      >
                        <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-slate-100">
                          <FileText className="size-5 text-slate-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm">{file.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {file.rows.toLocaleString()} rows • Uploaded{" "}
                            {file.date}
                          </p>
                        </div>
                        {file.status === "validated" ? (
                          <Badge color="green">
                            <CheckCircle2 className="size-3 mr-1" />
                            Validated
                          </Badge>
                        ) : (
                          <Badge color="orange">
                            <AlertCircle className="size-3 mr-1" />
                            Needs Mapping
                          </Badge>
                        )}
                        <Button variant="ghost" size="sm">
                          View
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Info Card */}
              <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
                <div className="flex gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-100">
                    <Database className="size-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm">
                      Once connected, data will flow automatically into the AI
                      pipeline
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Your data is processed securely and used only for
                      generating insights
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Preview Panel - 1 column */}
            <div>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Data Preview</CardTitle>
                  <CardDescription>customers.csv</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Total Rows</span>
                      <span>8,347</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        Total Columns
                      </span>
                      <span>12</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Date Range</span>
                      <span>2023-2025</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Customers</span>
                      <span>8,347</span>
                    </div>
                  </div>

                  <div className="border rounded-md overflow-hidden">
                    <div className="bg-slate-50 px-3 py-2 text-xs border-b">
                      Sample Data (First 5 rows)
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-2 py-1 text-left">CustomerID</th>
                            <th className="px-2 py-1 text-left">Name</th>
                            <th className="px-2 py-1 text-left">Segment</th>
                          </tr>
                        </thead>
                        <tbody className="text-muted-foreground">
                          <tr className="border-t">
                            <td className="px-2 py-1">C001</td>
                            <td className="px-2 py-1">Alice...</td>
                            <td className="px-2 py-1">Top</td>
                          </tr>
                          <tr className="border-t">
                            <td className="px-2 py-1">C002</td>
                            <td className="px-2 py-1">Bob...</td>
                            <td className="px-2 py-1">Mod.</td>
                          </tr>
                          <tr className="border-t">
                            <td className="px-2 py-1">C003</td>
                            <td className="px-2 py-1">Carol...</td>
                            <td className="px-2 py-1">Risk</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <Button variant="outline" size="sm" className="w-full">
                    View Full Dataset
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="cloud" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-blue-100 mb-2">
                  <Cloud className="size-6 text-blue-600" />
                </div>
                <CardTitle className="text-base">Amazon S3</CardTitle>
                <CardDescription>
                  Connect to your S3 buckets for automated data ingestion
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-orange-100 mb-2">
                  <Database className="size-6 text-orange-600" />
                </div>
                <CardTitle className="text-base">Google BigQuery</CardTitle>
                <CardDescription>
                  Query and analyze data from BigQuery datasets
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-cyan-100 mb-2">
                  <Cloud className="size-6 text-cyan-600" />
                </div>
                <CardTitle className="text-base">Snowflake</CardTitle>
                <CardDescription>
                  Connect to your Snowflake data warehouse
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-purple-100 mb-2">
                  <Database className="size-6 text-purple-600" />
                </div>
                <CardTitle className="text-base">Azure Data Lake</CardTitle>
                <CardDescription>
                  Connect to Azure storage for data analytics
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-red-100 mb-2">
                  <Cloud className="size-6 text-red-600" />
                </div>
                <CardTitle className="text-base">Databricks</CardTitle>
                <CardDescription>
                  Connect to Databricks lakehouse platform
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-green-100 mb-2">
                  <Database className="size-6 text-green-600" />
                </div>
                <CardTitle className="text-base">Redshift</CardTitle>
                <CardDescription>
                  Connect to Amazon Redshift warehouse
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sql" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-blue-100 mb-2">
                  <Database className="size-6 text-blue-600" />
                </div>
                <CardTitle className="text-base">PostgreSQL</CardTitle>
                <CardDescription>
                  Connect to PostgreSQL database
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-orange-100 mb-2">
                  <Database className="size-6 text-orange-600" />
                </div>
                <CardTitle className="text-base">MySQL</CardTitle>
                <CardDescription>Connect to MySQL database</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-slate-100 mb-2">
                  <Database className="size-6 text-slate-600" />
                </div>
                <CardTitle className="text-base">SQL Server</CardTitle>
                <CardDescription>
                  Connect to Microsoft SQL Server
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-red-100 mb-2">
                  <Database className="size-6 text-red-600" />
                </div>
                <CardTitle className="text-base">Oracle</CardTitle>
                <CardDescription>Connect to Oracle database</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-green-100 mb-2">
                  <Database className="size-6 text-green-600" />
                </div>
                <CardTitle className="text-base">MariaDB</CardTitle>
                <CardDescription>Connect to MariaDB database</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:border-teal-200 hover:shadow-sm transition-all cursor-pointer">
              <CardHeader>
                <div className="flex size-12 items-center justify-center rounded-md bg-purple-100 mb-2">
                  <Database className="size-6 text-purple-600" />
                </div>
                <CardTitle className="text-base">MongoDB</CardTitle>
                <CardDescription>Connect to MongoDB database</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Connect
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
