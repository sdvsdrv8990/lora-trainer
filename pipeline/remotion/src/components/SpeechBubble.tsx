import React from "react";

interface SpeechBubbleProps {
  text: string;
  style?: "oval_right" | "oval_left" | "thought";
}

export const SpeechBubble: React.FC<SpeechBubbleProps> = ({ text, style = "oval_right" }) => {
  const tailLeft = style === "oval_left";
  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <div
        style={{
          background: "#FFFFFF",
          border: "3px solid #222222",
          borderRadius: 24,
          padding: "8px 16px",
          fontSize: 28,
          fontWeight: "bold",
          fontFamily: "Arial, sans-serif",
          color: "#111111",
          maxWidth: 320,
          textAlign: "center",
          lineHeight: 1.3,
        }}
      >
        {text}
      </div>
      {/* Tail */}
      <div
        style={{
          position: "absolute",
          bottom: -16,
          [tailLeft ? "left" : "right"]: 24,
          width: 0,
          height: 0,
          borderLeft: "12px solid transparent",
          borderRight: "12px solid transparent",
          borderTop: "16px solid #222222",
        }}
      />
    </div>
  );
};
