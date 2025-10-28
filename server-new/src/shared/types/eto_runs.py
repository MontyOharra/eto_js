"""
ETO Run Types
Dataclasses for ETO processing lifecycle and state management
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Any

# TODO: Define domain dataclasses:
#
# Core Run Types:
# - EtoRun (complete run record from eto_runs table)
# - EtoRunListView (optimized view for list endpoint with joined data)
# - EtoRunDetail (full detail view with all stage data)
# - EtoRunCreate (data for creating new run)
#
# Stage Types:
# - EtoRunTemplateMatching (template_matching stage record)
# - EtoRunDataExtraction (data_extraction stage record)
# - EtoRunPipelineExecution (pipeline_execution stage record)
# - EtoPipelineExecutionStep (individual step record)
#
# Nested Types:
# - EtoPdfInfo (PDF file metadata)
# - EtoSourceManual (manual upload source)
# - EtoSourceEmail (email source with metadata)
# - EtoMatchedTemplate (matched template reference)
#
# Status Enums:
# - EtoRunStatus: Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
# - EtoProcessingStep: Literal["template_matching", "data_extraction", "data_transformation"]
# - EtoStageStatus: Literal["not_started", "success", "failure", "skipped"]
