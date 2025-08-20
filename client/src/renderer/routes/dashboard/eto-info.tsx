import { createFileRoute } from "@tanstack/react-router";
import { EtoRunsTable } from "../../components/EtoRunsTable";
import { mockEtoRuns, getEtoRunSummary } from "../../data/mockEtoRuns";

export const Route = createFileRoute("/dashboard/eto-info")({
  component: EtoInfoPage,
});

function EtoInfoPage() {
  // Group runs by status
  const successRuns = mockEtoRuns
    .filter((run) => run.status === "success")
    .map(getEtoRunSummary);

  const failureRuns = mockEtoRuns
    .filter((run) => run.status === "failure")
    .map(getEtoRunSummary);

  const unrecognizedRuns = mockEtoRuns
    .filter((run) => run.status === "unrecognized")
    .map(getEtoRunSummary);

  const handleView = (runId: string) => {
    console.log("View run:", runId);
    // TODO: Show run details modal
  };

  const handleReview = (runId: string) => {
    console.log("Review run:", runId);
    // TODO: Open review interface
  };

  return (
    <div className="flex-1 p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-blue-300 mb-2">
          ETO Information
        </h1>
        <p className="text-gray-400">
          Monitor and review PDF processing results
        </p>
      </div>

      <div className="space-y-6">
        <EtoRunsTable
          title="Successful Extractions"
          runs={successRuns}
          status="success"
          onView={handleView}
          onReview={handleReview}
        />

        <EtoRunsTable
          title="Failed Extractions"
          runs={failureRuns}
          status="failure"
          onView={handleView}
          onReview={handleReview}
        />

        <EtoRunsTable
          title="Unrecognized Attachments"
          runs={unrecognizedRuns}
          status="unrecognized"
          onView={handleView}
          onReview={handleReview}
        />
      </div>
    </div>
  );
}
