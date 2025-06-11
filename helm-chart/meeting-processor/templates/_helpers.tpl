{{/*
Expand the name of the chart.
*/}}
{{- define "meeting-processor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "meeting-processor.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "meeting-processor.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "meeting-processor.labels" -}}
helm.sh/chart: {{ include "meeting-processor.chart" . }}
{{ include "meeting-processor.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: meeting-processor
environment: {{ .Values.environment }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "meeting-processor.selectorLabels" -}}
app.kubernetes.io/name: {{ include "meeting-processor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Web selector labels
*/}}
{{- define "meeting-processor.web.selectorLabels" -}}
{{ include "meeting-processor.selectorLabels" . }}
app.kubernetes.io/component: web
{{- end }}

{{/*
Bot selector labels
*/}}
{{- define "meeting-processor.bot.selectorLabels" -}}
{{ include "meeting-processor.selectorLabels" . }}
app.kubernetes.io/component: bot
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "meeting-processor.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "meeting-processor.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Web image
*/}}
{{- define "meeting-processor.web.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- $repository := .Values.web.image.repository }}
{{- $tag := .Values.web.image.tag | default .Chart.AppVersion }}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Bot image
*/}}
{{- define "meeting-processor.bot.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- $repository := .Values.bot.image.repository }}
{{- $tag := .Values.bot.image.tag | default .Chart.AppVersion }}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}