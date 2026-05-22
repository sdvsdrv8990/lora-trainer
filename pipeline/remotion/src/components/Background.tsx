import React from "react";

interface BackgroundProps {
  color?: string;
  imagePath?: string;
  width: number;
  height: number;
}

export const Background: React.FC<BackgroundProps> = ({
  color = "#FFFFFF",
  imagePath,
  width,
  height,
}) => {
  if (imagePath) {
    return (
      <img
        src={imagePath}
        style={{ position: "absolute", width, height, objectFit: "cover" }}
      />
    );
  }
  return (
    <div
      style={{ position: "absolute", width, height, backgroundColor: color }}
    />
  );
};
