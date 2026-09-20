# AI-Readiness Check

DSAgt is configured at init to run [AIDRIN](https://github.com/idtlab/AIDRIN) (AI Data Readiness Inspector) as the check before and after every tabular pipeline stage; uncheck it on the menu to turn it off. AIDRIN installs with dsagt, and every project gets the `aidrin` skill and an `aidrin` code, so each call the agent makes is an execution record in `trace_archive/` like any other code. A user who asks "is my data AI-ready?" gets the AIDRIN skill's workflow.

With the check on, every table a pipeline step reads or writes gets an AIDRIN data-quality report. After a registered code exits, `dsagt-run` prints a note for each table of that run (a CSV, TSV, Parquet, or Excel file) that has no report for its current content:

```text
dsagt: no readiness report for data/clean.csv at its current content. Check it with the aidrin skill (at least its data-quality summary) before the next pipeline step.
```

The note is printed where the agent reads a command's output, which is when it chooses its next step. The agent checks the table with the `aidrin` skill through the project's registered `aidrin` code, and that run's execution record is the report: it holds what AIDRIN printed and the hash of the table it read. Once such a record exists the note stops, until the table's content changes. An input the step left unchanged is covered the same way, so the report on one step's output is the report on the next step's input.

The `readiness_reports` tool gives the same answer on request. For a data file it returns the current report's text, or says there is none and how to make one, and lists the reports from before the file changed. A user who asks "is this file AI-ready?" gets the existing report or a new check. A quality score is comparable between a table's own reports, and between a table and the one it was made from; two unrelated tables' scores are not a trend.

`dsagt init` asks "Assess tabular data for AI-readiness before and after each data transform?", default yes (`--no-readiness` declines). The answer is the `readiness.auto_assess` setting in `.dsagt/config.yaml`, which `dsagt-run` reads at each run; the `aidrin` code and skill are present either way. JSON, HDF5 and NumPy files are tables only sometimes, so they get no note; ask for a check and the skill decides.

## Try it

A three-stage pipeline on AIDRIN's own demo dataset: 525 sensor readings with 25 exact
duplicates, missing values in every sensor column, and temperature outliers. About ten minutes;
the only download is a 40 KB CSV.

```bash
dsagt init
```

At the menu, name the project `assessment-demo`, pick your agent, leave the knowledge
collections and skill sources unchecked (the check needs neither), and keep the
AI-readiness check on. Then:

```bash
mkdir -p ~/dsagt-projects/assessment-demo/data
curl -sL https://raw.githubusercontent.com/idtlab/AIDRIN/develop/demos/messy_sensor_data.csv \
    -o ~/dsagt-projects/assessment-demo/data/sensors.csv
dsagt start assessment-demo
```

Then one prompt. Leave AIDRIN and checks out of it; the demo shows what the agent does unprompted:

```text
Build a curation pipeline for data/sensors.csv in three steps, one at a time:
1. drop exact duplicate rows -> data/dedup.csv
2. drop rows with a missing temperature -> data/complete.csv
3. drop rows whose temperature is more than 3 standard deviations from the mean -> data/clean.csv
Confirm the approach with me before each step.
```

After each stage `dsagt-run` notes the tables with no report, and the agent should check them with
the aidrin skill and show the metric change before proposing the next step. Expected values on this dataset (pre column measured directly):

| Stage | Metric | pre | post |
|---|---|---|---|
| 1 dedup | duplicity | 0.0476 | 0.0 |
| 2 complete | completeness (`temperature`) | 0.8457 | 1.0 |
| 3 outliers | outliers (`temperature`) | 0.0225 | lower |

Afterwards, one more prompt:

```text
Show me the execution records for this session as a table of step, command, and exit code.
```

The table lists one record per operation and one per check: the input once, then each stage's
output, since a stage's output is the next stage's input. Clean up with `dsagt rm assessment-demo -y`.

## Demos

The [cryo-EM curation demo](use-cases/cryoem.md) runs on real scientific data; the check measures the particle-curation step unprompted. The [AIDRIN example](use-cases/aidrin-ai-readiness.md) drives quality, fairness, and privacy metrics on a tabular dataset.
