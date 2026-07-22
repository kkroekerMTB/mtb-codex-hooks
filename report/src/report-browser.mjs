import Chart from "chart.js/auto";

const report = window.__CODEX_HOOKS_REPORT__;
const colors = {
  blue: "#2563eb",
  cyan: "#0891b2",
  gold: "#d97706",
  green: "#059669",
  purple: "#7c3aed",
  red: "#dc2626",
  slate: "#64748b",
};

document.querySelector("[data-value='cost']").textContent = currency(
  report.summary.estimatedCost,
);
document.querySelector("[data-value='tokens']").textContent = integer(
  report.summary.totalTokens,
);
document.querySelector("[data-value='cache']").textContent = percent(
  report.summary.cacheHitRate,
);
document.querySelector("[data-value='calls']").textContent = integer(
  report.summary.modelCalls,
);
document.querySelector("[data-value='sessions']").textContent = integer(
  report.summary.sessions,
);

if (report.summary.unpricedModels.length > 0) {
  const warning = document.querySelector("[data-unpriced-models]");
  warning.hidden = false;
  warning.textContent = `No price configured for: ${report.summary.unpricedModels.join(", ")}. Their tokens are shown but excluded from estimated cost.`;
}

new Chart(document.querySelector("#token-timeline"), {
  type: "line",
  data: {
    labels: report.timeline.map((row) => row.date),
    datasets: [
      dataset("Uncached input", "uncachedInput", colors.blue),
      dataset("Cached input", "cachedInput", colors.cyan),
      dataset("Cache writes", "cacheWrite", colors.gold),
      dataset("Visible output", "visibleOutput", colors.green),
      dataset("Reasoning output", "reasoningOutput", colors.purple),
      {
        label: "Estimated cost",
        data: report.timeline.map((row) => row.estimatedCost),
        borderColor: colors.slate,
        backgroundColor: colors.slate,
        borderDash: [6, 4],
        fill: false,
        pointRadius: 3,
        tension: 0.25,
        yAxisID: "cost",
      },
    ],
  },
  options: tokenTimelineOptions(),
});

new Chart(document.querySelector("#model-reasoning"), {
  type: "doughnut",
  data: {
    labels: report.modelReasoning.map((row) => row.label),
    datasets: [
      {
        data: report.modelReasoning.map((row) => row.tokens),
        backgroundColor: palette(report.modelReasoning.length),
        borderWidth: 2,
        borderColor: "#fff",
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          afterLabel(context) {
            return `Estimated cost: ${currency(report.modelReasoning[context.dataIndex].estimatedCost)}`;
          },
        },
      },
    },
  },
});

new Chart(document.querySelector("#skills"), {
  type: "bar",
  data: {
    labels: report.skills.map((row) => row.name),
    datasets: [
      {
        label: "Invocations",
        data: report.skills.map((row) => row.count),
        backgroundColor: colors.purple,
        borderRadius: 5,
      },
    ],
  },
  options: chartOptions({ horizontal: true, integersOnly: true }),
});

new Chart(document.querySelector("#tools"), {
  type: "bar",
  data: {
    labels: report.tools.map((row) => row.name),
    datasets: [
      {
        label: "Completed",
        data: report.tools.map((row) => row.completed),
        backgroundColor: colors.blue,
        borderRadius: 5,
      },
      {
        label: "Incomplete",
        data: report.tools.map((row) => row.incomplete),
        backgroundColor: colors.red,
        borderRadius: 5,
      },
    ],
  },
  options: {
    ...chartOptions({ horizontal: true, integersOnly: true, stacked: true }),
    plugins: {
      tooltip: {
        callbacks: {
          afterBody(items) {
            const tool = report.tools[items[0].dataIndex];
            const toolCalls = tool.completed + tool.incomplete;
            const details = [
              `Share of all calls: ${percent(toolCalls / report.summary.toolCalls)}`,
            ];
            if (tool.averageDurationMs !== null) {
              details.push(
                `Average completed duration: ${integer(tool.averageDurationMs)} ms`,
              );
            }
            return details;
          },
        },
      },
    },
  },
});

function dataset(label, field, color) {
  return {
    label,
    data: report.timeline.map((row) => row[field]),
    borderColor: color,
    backgroundColor: `${color}bf`,
    fill: true,
    pointRadius: report.timeline.length > 40 ? 0 : 3,
    tension: 0.25,
  };
}

function chartOptions({ horizontal = false, integersOnly = false, stacked = false }) {
  const valueAxis = horizontal ? "x" : "y";
  const categoryAxis = horizontal ? "y" : "x";
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? "y" : "x",
    interaction: { intersect: false, mode: "index" },
    scales: {
      [valueAxis]: {
        beginAtZero: true,
        stacked,
        ticks: integersOnly ? { precision: 0 } : {},
      },
      [categoryAxis]: { stacked },
    },
  };
}

function tokenTimelineOptions() {
  const options = chartOptions({ stacked: true });
  options.scales.cost = {
    position: "right",
    beginAtZero: true,
    grid: { drawOnChartArea: false },
    ticks: { callback: (value) => currency(value) },
    title: { display: true, text: "Estimated USD" },
  };
  return options;
}

function palette(count) {
  const values = Object.values(colors);
  return Array.from({ length: count }, (_, index) => values[index % values.length]);
}

function integer(value) {
  return new Intl.NumberFormat().format(value);
}

function currency(value) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 0.01 ? 4 : 2,
    maximumFractionDigits: value < 0.01 ? 6 : 2,
  }).format(value);
}

function percent(value) {
  return new Intl.NumberFormat(undefined, {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}
