"use client";

/**
 * PathVisualization Component
 *
 * Real-time 2D Canvas visualization for robot navigation
 */

import { useEffect, useRef, useState } from "react";
import {
  VisualizationState,
  VisualizationConfig,
  DEFAULT_VIZ_CONFIG,
  Point2D,
  RobotPose,
  Obstacle,
  PlannedPath,
  Formation,
  DemoDataGenerator,
} from "@/lib/pathVisualization";

interface PathVisualizationProps {
  config?: Partial<VisualizationConfig>;
  className?: string;
  updateInterval?: number; // milliseconds
}

export function PathVisualization({
  config: partialConfig,
  className = "",
  updateInterval = 100, // 10 FPS
}: PathVisualizationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [vizState, setVizState] = useState<VisualizationState | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const demoGeneratorRef = useRef<DemoDataGenerator | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const lastUpdateRef = useRef<number>(Date.now());

  const config: VisualizationConfig = {
    ...DEFAULT_VIZ_CONFIG,
    ...partialConfig,
  };

  // Initialize demo data generator
  useEffect(() => {
    if (!demoGeneratorRef.current) {
      demoGeneratorRef.current = new DemoDataGenerator(5);
    }
  }, []);

  // Animation loop
  useEffect(() => {
    if (isPaused || !demoGeneratorRef.current) return;

    const animate = () => {
      const now = Date.now();
      const deltaTime = (now - lastUpdateRef.current) / 1000; // Convert to seconds
      lastUpdateRef.current = now;

      const newState = demoGeneratorRef.current!.update(deltaTime);
      setVizState(newState);

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPaused]);

  // Render canvas
  useEffect(() => {
    if (!vizState || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    renderVisualization(ctx, vizState, config);
  }, [vizState, config]);

  // World to canvas coordinate conversion
  const worldToCanvas = (point: Point2D, config: VisualizationConfig): Point2D => {
    const centerX = config.canvas_width / 2;
    const centerY = config.canvas_height / 2;
    const scale = 1 / config.meters_per_pixel;

    return {
      x: centerX + point.x * scale,
      y: centerY - point.y * scale, // Flip Y axis (canvas Y increases downward)
    };
  };

  const renderVisualization = (
    ctx: CanvasRenderingContext2D,
    state: VisualizationState,
    config: VisualizationConfig
  ) => {
    // Clear canvas
    ctx.fillStyle = config.colors.background;
    ctx.fillRect(0, 0, config.canvas_width, config.canvas_height);

    // Draw grid
    if (config.show_grid) {
      drawGrid(ctx, state, config);
    }

    // Draw formations
    if (config.show_formations) {
      state.formations.forEach((formation) => drawFormation(ctx, formation, config));
    }

    // Draw planned paths
    if (config.show_paths) {
      state.paths.forEach((path) => drawPath(ctx, path, config));
    }

    // Draw obstacles
    state.obstacles.forEach((obstacle) => drawObstacle(ctx, obstacle, config));

    // Draw robots
    state.robots.forEach((robot) => drawRobot(ctx, robot, config));

    // Draw timestamp
    ctx.fillStyle = config.colors.text;
    ctx.font = "12px monospace";
    ctx.fillText(`t: ${(state.timestamp / 1000).toFixed(1)}s`, 10, 20);
    ctx.fillText(`Robots: ${state.robots.length}`, 10, 40);
    ctx.fillText(`Obstacles: ${state.obstacles.length}`, 10, 60);
  };

  const drawGrid = (
    ctx: CanvasRenderingContext2D,
    state: VisualizationState,
    config: VisualizationConfig
  ) => {
    ctx.strokeStyle = config.colors.grid;
    ctx.lineWidth = 1;

    const { min_x, max_x, min_y, max_y } = state.world_bounds;
    const spacing = config.grid_spacing_meters;

    // Vertical lines
    for (let x = min_x; x <= max_x; x += spacing) {
      const start = worldToCanvas({ x, y: min_y }, config);
      const end = worldToCanvas({ x, y: max_y }, config);
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
    }

    // Horizontal lines
    for (let y = min_y; y <= max_y; y += spacing) {
      const start = worldToCanvas({ x: min_x, y }, config);
      const end = worldToCanvas({ x: max_x, y }, config);
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
    }

    // Draw origin
    ctx.strokeStyle = config.colors.text;
    ctx.lineWidth = 2;
    const origin = worldToCanvas({ x: 0, y: 0 }, config);
    ctx.beginPath();
    ctx.moveTo(origin.x - 10, origin.y);
    ctx.lineTo(origin.x + 10, origin.y);
    ctx.moveTo(origin.x, origin.y - 10);
    ctx.lineTo(origin.x, origin.y + 10);
    ctx.stroke();
  };

  const drawRobot = (
    ctx: CanvasRenderingContext2D,
    robot: RobotPose,
    config: VisualizationConfig
  ) => {
    const pos = worldToCanvas(robot.position, config);
    const radius = config.robot_radius_meters / config.meters_per_pixel;

    // Robot body
    const colorMap = {
      idle: config.colors.robot_idle,
      moving: config.colors.robot_moving,
      charging: config.colors.robot_charging,
      error: config.colors.robot_error,
    };
    ctx.fillStyle = colorMap[robot.status];
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
    ctx.fill();

    // Orientation indicator
    ctx.strokeStyle = config.colors.background;
    ctx.lineWidth = 3;
    const orientEnd = {
      x: pos.x + Math.cos(robot.orientation_rad) * radius * 1.5,
      y: pos.y - Math.sin(robot.orientation_rad) * radius * 1.5,
    };
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    ctx.lineTo(orientEnd.x, orientEnd.y);
    ctx.stroke();

    // Robot ID
    if (config.show_robot_ids) {
      ctx.fillStyle = config.colors.text;
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      ctx.fillText(robot.robot_id.replace("robot_", "R"), pos.x, pos.y + radius + 12);
    }

    // Velocity vector
    if (config.show_velocities && robot.velocity > 0) {
      ctx.strokeStyle = config.colors.robot_moving;
      ctx.lineWidth = 2;
      const velEnd = {
        x: pos.x + Math.cos(robot.orientation_rad) * robot.velocity * 50,
        y: pos.y - Math.sin(robot.orientation_rad) * robot.velocity * 50,
      };
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      ctx.lineTo(velEnd.x, velEnd.y);
      ctx.stroke();

      // Arrow head
      const arrowSize = 5;
      const angle = robot.orientation_rad;
      ctx.beginPath();
      ctx.moveTo(velEnd.x, velEnd.y);
      ctx.lineTo(
        velEnd.x - arrowSize * Math.cos(angle - Math.PI / 6),
        velEnd.y + arrowSize * Math.sin(angle - Math.PI / 6)
      );
      ctx.moveTo(velEnd.x, velEnd.y);
      ctx.lineTo(
        velEnd.x - arrowSize * Math.cos(angle + Math.PI / 6),
        velEnd.y + arrowSize * Math.sin(angle + Math.PI / 6)
      );
      ctx.stroke();
    }

    // Battery indicator
    const batteryWidth = 30;
    const batteryHeight = 5;
    const batteryX = pos.x - batteryWidth / 2;
    const batteryY = pos.y - radius - 15;

    ctx.strokeStyle = config.colors.text;
    ctx.lineWidth = 1;
    ctx.strokeRect(batteryX, batteryY, batteryWidth, batteryHeight);

    const batteryFill = (robot.battery_percent / 100) * batteryWidth;
    ctx.fillStyle =
      robot.battery_percent > 50
        ? config.colors.robot_moving
        : robot.battery_percent > 20
          ? config.colors.robot_charging
          : config.colors.robot_error;
    ctx.fillRect(batteryX, batteryY, batteryFill, batteryHeight);
  };

  const drawObstacle = (
    ctx: CanvasRenderingContext2D,
    obstacle: Obstacle,
    config: VisualizationConfig
  ) => {
    const pos = worldToCanvas(obstacle.position, config);
    const radius = obstacle.radius / config.meters_per_pixel;

    const colorMap = {
      static: config.colors.obstacle_static,
      dynamic: config.colors.obstacle_dynamic,
      human: config.colors.obstacle_human,
      robot: config.colors.robot_idle,
    };

    ctx.fillStyle = colorMap[obstacle.type];
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
    ctx.fill();
    ctx.globalAlpha = 1.0;

    // Draw velocity vector for dynamic obstacles
    if (obstacle.velocity && (obstacle.velocity.x !== 0 || obstacle.velocity.y !== 0)) {
      ctx.strokeStyle = colorMap[obstacle.type];
      ctx.lineWidth = 2;
      const velEnd = {
        x: pos.x + obstacle.velocity.x * 100,
        y: pos.y - obstacle.velocity.y * 100,
      };
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      ctx.lineTo(velEnd.x, velEnd.y);
      ctx.stroke();
    }
  };

  const drawPath = (
    ctx: CanvasRenderingContext2D,
    path: PlannedPath,
    config: VisualizationConfig
  ) => {
    ctx.strokeStyle = config.colors.path;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.globalAlpha = 0.7;

    path.segments.forEach((segment) => {
      const start = worldToCanvas(segment.start, config);
      const end = worldToCanvas(segment.end, config);

      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
    });

    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;
  };

  const drawFormation = (
    ctx: CanvasRenderingContext2D,
    formation: Formation,
    config: VisualizationConfig
  ) => {
    const center = worldToCanvas(formation.center, config);

    ctx.strokeStyle = config.colors.formation;
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 5]);
    ctx.globalAlpha = 0.5;

    // Draw formation boundary (simple circle for demo)
    const radius = formation.scale * 100;
    ctx.beginPath();
    ctx.arc(center.x, center.y, radius, 0, 2 * Math.PI);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;

    // Formation label
    ctx.fillStyle = config.colors.text;
    ctx.font = "12px monospace";
    ctx.textAlign = "center";
    ctx.fillText(`Formation: ${formation.type}`, center.x, center.y - radius - 10);
  };

  return (
    <div className={`relative ${className}`}>
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={config.canvas_width}
        height={config.canvas_height}
        className="border border-gray-700 rounded-lg"
      />

      {/* Controls */}
      <div className="absolute top-2 right-2 flex flex-col gap-2">
        <button
          onClick={() => setIsPaused(!isPaused)}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
        >
          {isPaused ? "▶ Resume" : "⏸ Pause"}
        </button>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded"
        >
          ⚙ Settings
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="absolute top-12 right-2 bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm w-64">
          <h3 className="font-semibold mb-2">Visualization Settings</h3>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={config.show_grid} readOnly />
              <span>Show Grid</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={config.show_robot_ids} readOnly />
              <span>Show Robot IDs</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={config.show_velocities} readOnly />
              <span>Show Velocities</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={config.show_paths} readOnly />
              <span>Show Paths</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={config.show_formations} readOnly />
              <span>Show Formations</span>
            </label>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span>Idle Robot</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span>Moving Robot</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500"></div>
          <span>Charging Robot</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span>Error Robot</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gray-500"></div>
          <span>Static Obstacle</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-pink-500"></div>
          <span>Human</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-violet-500" style={{ clipPath: "polygon(0 50%, 100% 0, 100% 100%)" }}></div>
          <span>Planned Path</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 border-2 border-teal-500 rounded-full"></div>
          <span>Formation</span>
        </div>
      </div>
    </div>
  );
}
