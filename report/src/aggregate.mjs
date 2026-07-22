export function estimateModelCallCost(modelCall, pricing) {
  const modelRates = pricing.models[modelCall.model];
  if (!modelRates) {
    return null;
  }

  const rates =
    nonNegativeNumber(modelCall.input_tokens) > pricing.longContextThreshold &&
    modelRates.longContext
      ? modelRates.longContext
      : modelRates;

  const unit = pricing.unitTokens;
  return (
    (nonNegativeNumber(modelCall.uncached_input_tokens) * rates.input +
      nonNegativeNumber(modelCall.cached_input_tokens) * rates.cachedInput +
      nonNegativeNumber(modelCall.cache_write_input_tokens) * rates.cacheWrite +
      nonNegativeNumber(modelCall.output_tokens) * rates.output) /
    unit
  );
}

export function buildReportData({ modelCalls, skills, tools }, pricing) {
  const timeline = new Map();
  const modelReasoning = new Map();
  const sessions = new Set();
  const unpricedModels = new Set();
  let totalTokens = 0;
  let totalInputTokens = 0;
  let totalCachedInputTokens = 0;
  let estimatedCost = 0;

  for (const call of modelCalls) {
    const date = call.model_call_timestamp?.slice(0, 10);
    if (!date) {
      continue;
    }

    const cost = estimateModelCallCost(call, pricing);
    if (cost === null) {
      unpricedModels.add(call.model || "unknown");
    } else {
      estimatedCost += cost;
    }

    const values = {
      uncachedInput: nonNegativeNumber(call.uncached_input_tokens),
      cachedInput: nonNegativeNumber(call.cached_input_tokens),
      cacheWrite: nonNegativeNumber(call.cache_write_input_tokens),
      visibleOutput: nonNegativeNumber(call.visible_output_tokens),
      reasoningOutput: nonNegativeNumber(call.reasoning_output_tokens),
      estimatedCost: cost || 0,
    };
    addToGroup(timeline, date, values);

    const label = `${call.model || "unknown"} / ${call.reasoning_effort || "unknown"}`;
    addToGroup(modelReasoning, label, {
      tokens: nonNegativeNumber(call.total_tokens),
      estimatedCost: cost || 0,
    });

    totalTokens += nonNegativeNumber(call.total_tokens);
    totalInputTokens += nonNegativeNumber(call.input_tokens);
    totalCachedInputTokens += nonNegativeNumber(call.cached_input_tokens);
    if (call.session_id) {
      sessions.add(call.session_id);
    }
  }

  return {
    summary: {
      totalTokens,
      modelCalls: modelCalls.length,
      toolCalls: tools.length,
      sessions: sessions.size,
      estimatedCost,
      cacheHitRate:
        totalInputTokens === 0 ? 0 : totalCachedInputTokens / totalInputTokens,
      unpricedModels: [...unpricedModels].sort(),
    },
    timeline: namedGroups(timeline, "date"),
    modelReasoning: namedGroups(modelReasoning, "label").sort(
      (left, right) => right.tokens - left.tokens,
    ),
    skills: countByName(skills, "skill_name"),
    tools: summarizeTools(tools),
    pricing: {
      name: pricing.name,
      effectiveDate: pricing.effectiveDate,
      source: pricing.source,
      unitTokens: pricing.unitTokens,
    },
  };
}

function addToGroup(groups, key, values) {
  const group = groups.get(key) || {};
  for (const [name, value] of Object.entries(values)) {
    group[name] = (group[name] || 0) + value;
  }
  groups.set(key, group);
}

function namedGroups(groups, nameKey) {
  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, values]) => ({ [nameKey]: name, ...values }));
}

function countByName(rows, field) {
  const counts = new Map();
  for (const row of rows) {
    const name = row[field];
    if (name) {
      counts.set(name, (counts.get(name) || 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
}

function summarizeTools(rows) {
  const groups = new Map();
  for (const row of rows) {
    const name = row.tool_name || "unknown";
    const group = groups.get(name) || {
      name,
      completed: 0,
      incomplete: 0,
      durations: [],
    };
    if (row.status === "completed") {
      group.completed += 1;
      if (row.duration_ms !== "" && Number.isFinite(Number(row.duration_ms))) {
        group.durations.push(Number(row.duration_ms));
      }
    } else {
      group.incomplete += 1;
    }
    groups.set(name, group);
  }

  return [...groups.values()]
    .map(({ name, completed, incomplete, durations }) => ({
      name,
      completed,
      incomplete,
      averageDurationMs:
        durations.length === 0
          ? null
          : Math.round(
              durations.reduce((sum, duration) => sum + duration, 0) /
                durations.length,
            ),
    }))
    .sort(
      (left, right) =>
        right.completed + right.incomplete - (left.completed + left.incomplete) ||
        left.name.localeCompare(right.name),
    );
}

function nonNegativeNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}
