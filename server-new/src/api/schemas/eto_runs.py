"""
ETO Runs API Schemas
Pydantic models for ETO run endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field

# TODO: Define schemas for ETO runs endpoints
# - EtoRunListItem (GET /eto-runs response)
# - EtoRunDetail (GET /eto-runs/{id} response)
# - PostEtoRunUploadResponse (POST /eto-runs/upload response)
# - PostEtoRunsReprocessRequest (POST /eto-runs/reprocess request)
# - PostEtoRunsSkipRequest (POST /eto-runs/skip request)
# - DeleteEtoRunsRequest (DELETE /eto-runs request)
#
# Stage types:
# - EtoStageTemplateMatching
# - EtoStageDataExtraction
# - EtoStagePipelineExecution
# - EtoPipelineExecutionStep
#
# Nested types:
# - EtoPdfInfo
# - EtoSource (discriminated union: manual | email)
# - EtoMatchedTemplate
