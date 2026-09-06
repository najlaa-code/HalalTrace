import React from "react";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

export default function Sparkline({ data, color }) {
  return (
    <div style={{ height: 46, width: "100%" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, bottom: 4, left: 0, right: 0 }}>
          <YAxis hide domain={["dataMin - 1", "dataMax + 1"]} />
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2.4} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
