---
name: auto-flex
description: Turn a natural-language laboratory experiment request or an existing Python protocol into a documented, simulated, and optionally executed Opentrons Flex workflow. Use for generating new Flex protocols or validating and running supplied `.py` protocols; do not use for OT-2-only workflows.
---

# Auto Flex

Create a traceable Flex experiment package. Route new experiment requests through planning and generation; route supplied Python protocols directly through documentation, simulation, and live execution.

## Required resources

- Treat `references/Flex_API_Documentation.md` as the protocol-authoring source of truth.
- Query its local BM25 index with `scripts/query_flex_docs.py`; do not load the entire document unless targeted retrieval is insufficient.
- Use `scripts/confirm_plan.ps1` for the plan-review dialog.
- Use `scripts/run_simulation.ps1` for every simulation attempt.
- Use `scripts/flex_env.py` to read and update the persistent `.env` hardware profile.
- Use the configured `opentrons` MCP server only for live robot communication.

Resolve all relative resource paths from this skill directory.

## Safety and authorization

- A timed plan confirmation approves only the written plan. It never authorizes physical robot actions.
- Immediately before uploading or starting a real run, obtain explicit user confirmation that names the robot IP and protocol file. Do not use a timeout or inferred consent for this confirmation.
- Do not open the timed plan dialog while a critical parameter is unresolved. Ask for missing values first when volumes, source/destination mapping, labware identity, pipette, module, temperature, timing, or robot IP cannot be safely inferred.
- Never bypass a failed simulation. Never invent a labware load name or API call; retrieve it from the bundled documentation or ask the user.
- Stop after five simulation repair attempts, or after the same substantive error occurs twice. Preserve logs and ask the user for direction.
- During a live run, do not call unrelated hardware-control tools. If the robot reports a fault, pause/stop when the API supports it, record the result, and ask the user before attempting recovery.
- Never edit or overwrite a user-supplied protocol in place. Copy it into the experiment directory and repair only that working copy.
- Treat `.env` hardware data as machine-specific. Do not expose the robot serial unnecessarily or commit a populated hardware profile to a public repository.

## Artifact layout

Run `scripts/new_experiment.py --root <workspace>` once. It creates and returns a unique folder named `YYYY-MM-DD_expNN`. Keep every artifact from this workflow inside it:

```text
YYYY-MM-DD_expNN/
  exp_NN.md
  plan_confirmation_NN_attempt_01.json
  protocol_NN.py
  simulation_NN_attempt_01.log
  live_run_NN.log
```

Never overwrite attempt logs. Use the numeric suffix returned by the initializer for all primary filenames.

## Workflow

### 0. Load or discover the Flex hardware profile

Perform this preflight before choosing either input route and before writing an experiment plan, experiment introduction, or protocol.

1. Read the skill-root `.env` with:

   ```powershell
   python scripts/flex_env.py --env .env status
   ```

2. Use `DEFAULT_IP` as the robot IP unless the user explicitly supplies another IP.
3. If `HEARD_Flex=True`, do not query the robot for hardware discovery again. Use the cached `.env` fields for this invocation.
4. If `HEARD_Flex` is absent or not `True`, call the `opentrons` MCP tool `robot_health` with `DEFAULT_IP`. Parse the returned robot name, API version, firmware version, system version, robot model, and robot serial. Only after a successful response, persist them with:

   ```powershell
   python scripts/flex_env.py --env .env write-health `
     --robot-name <name> `
     --api-version <api-version> `
     --firmware-version <firmware-version> `
     --system-version <system-version> `
     --robot-model <model> `
     --robot-serial <serial>
   ```

   This command sets `HEARD_Flex=True` and records the UTC refresh time. Do not set the flag when the MCP call fails or returns an unusable response; report the connection problem and stop before plan or protocol generation.
5. Accept Flex-family identifiers such as `Flex`, `OT-3`, or `OT-3 Standard`; stop only if the response identifies an OT-2 or another clearly non-Flex robot. If the response omits a field, store `Unknown` rather than inventing a value.
6. Use the loaded hardware profile as an input to every generated `exp_NN.md` and `protocol_NN.py`:
   - Add a **Detected Flex hardware** section to the plan or experiment introduction with the effective IP, model, software/API/firmware versions, robot name, and discovery timestamp. Include the serial only when it is operationally useful.
   - Validate that selected pipettes, modules, labware, API features, and robot type are compatible with the detected Flex profile.
   - Add a concise generated-code comment identifying the target model and relevant software/API versions. Do not place secrets or the robot serial in protocol source.
   - Keep the protocol's Python Protocol API level based on the protocol documentation and supported feature requirements; do not copy the HTTP API version into `requirements["apiLevel"]`.

When the robot or its hardware changes, reset discovery with `python scripts/flex_env.py --env .env reset`; the next skill invocation must query `robot_health` again.

### Choose the input route

- **New protocol route:** The user describes an experiment but does not provide a Python protocol. Execute steps 1 through 4.
- **Existing protocol route:** The user attaches, references, or provides the path to a `*.py` protocol. Create the experiment directory, copy the source to `protocol_NN.py`, generate `exp_NN.md` as the detailed experiment introduction described below, skip steps 1 and 2, then execute steps 3 and 4. Do not show the timed plan-confirmation dialog for this route.

For the existing protocol route:

1. Confirm that the source file exists, is readable, and declares or clearly implements an Opentrons Flex protocol. Stop if it targets OT-2 or is not an Opentrons protocol.
2. Preserve the source file unchanged. Record its absolute source path and SHA-256 hash in `exp_NN.md`, then copy it to the experiment directory as `protocol_NN.py`. Apply all simulation-driven repairs only to this copy.
3. Derive a detailed experiment introduction from both the user's text and the protocol code. Include purpose, protocol metadata and API level, reagents/liquids that can be inferred, labware load names and slots, pipettes and tips, modules, deck layout, source/destination well mapping, volumes, mixing and flow settings, ordered operations, runtime parameters, expected outputs, waste handling, and safety/physical setup checks. Clearly label details that cannot be inferred; do not invent them.
4. The generated `exp_NN.md` is descriptive documentation, not a new plan requiring the 30-second approval dialog. Include the cached `.env` hardware profile and check the supplied protocol against it. Unless the user explicitly requests simulation only, proceed to step 4 after step 3 succeeds.

### 1. Draft and confirm the experiment plan

1. Convert the user's request and the loaded `.env` hardware profile into `exp_NN.md`. Include the detected Flex hardware section, objective, assumptions, samples/reagents, exact volumes and well mapping, labware load names, pipette/tips, modules, deck layout, ordered operations, mixing/flow-rate details, runtime parameters, controls, expected outputs, waste handling, and safety checks.
2. Mark any unresolved critical item as `BLOCKER` and resolve it with the user before continuing.
3. Show the plan in the timed dialog:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/confirm_plan.ps1 `
     -PlanPath <absolute-exp-path> `
     -ResultPath <absolute-confirmation-json-path> `
     -TimeoutSeconds 30
   ```

4. Interpret the returned JSON:
   - `confirmed`: continue. `source: timeout` means the 30-second countdown auto-confirmed the plan.
   - `revise`: incorporate the submitted feedback into the same plan, increment the confirmation-attempt number, and repeat this step.
   - `cancelled`: stop and ask the user how to proceed.

### 2. Retrieve API guidance and generate the protocol

1. Build the index only if missing or stale:

   ```powershell
   python scripts/build_rag_index.py references/Flex_API_Documentation.md references/flex_api_index.json
   ```

2. Run several focused retrievals that cover the confirmed plan, for example deck layout, exact labware and pipette names, module calls, liquid handling, gripper movement, and runtime parameters:

   ```powershell
   python scripts/query_flex_docs.py --index references/flex_api_index.json --top-k 5 "<focused query>"
   ```

3. Generate `protocol_NN.py` from the confirmed plan, retrieved passages, and loaded `.env` hardware profile. Target the detected Flex model and API level 2.29 unless the user explicitly requests another supported level. Keep configuration values visible, add a non-sensitive target-hardware comment, and add protocol comments at operational boundaries.
4. Ensure the code implements the confirmed well mapping and volumes exactly. Do not silently simplify the experiment.

### 3. Simulate and repair

1. Run the command-line simulator and capture a fresh log:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_simulation.ps1 `
     -ProtocolPath <absolute-protocol-path> `
     -LogPath <absolute-attempt-log-path>
   ```

2. Treat a nonzero exit code, traceback, analysis error, labware/module conflict, or unsupported API call as a failure.
3. Use the log plus targeted RAG retrieval to repair `protocol_NN.py`, then simulate again with the next attempt number.
4. Continue only when the simulator exits successfully and the log contains no protocol-analysis error. Summarize any warnings that remain.

If `opentrons_simulate` is unavailable, run `scripts/setup_simulator.ps1` once to create the isolated simulator environment, then retry.

### 4. Execute on the real Flex

After the separate explicit live-run confirmation:

1. Call `upload_protocol` with the confirmed effective robot IP (the user's override or `.env` `DEFAULT_IP`) and absolute `protocol_NN.py` path.
2. Record the returned protocol ID in `live_run_NN.log`.
3. Call `create_run` with that protocol ID; record the run ID.
4. Call `control_run` with action `play`.
5. Poll `get_run_status` at a reasonable interval until the run reaches a terminal state. Append timestamped status changes and errors to `live_run_NN.log`; avoid noisy duplicate entries.
6. Report the final state and artifact paths. Do not claim success unless the robot reports successful completion.
