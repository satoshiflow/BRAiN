/**
 * Path Visualization - Types and Data Structures
 *
 * 2D Canvas-based visualization for robot navigation
 */

// ========== Core Types ==========

export interface Point2D {
  x: number;
  y: number;
}

export interface RobotPose {
  robot_id: string;
  position: Point2D;
  orientation_rad: number; // Radians, 0 = East, π/2 = North
  velocity: number; // m/s
  status: "idle" | "moving" | "charging" | "error";
  battery_percent: number;
}

export interface PathSegment {
  start: Point2D;
  end: Point2D;
  cost: number;
}

export interface PlannedPath {
  robot_id: string;
  segments: PathSegment[];
  total_cost: number;
  eta_seconds: number;
}

export interface Obstacle {
  id: string;
  type: "static" | "dynamic" | "human" | "robot";
  position: Point2D;
  radius: number; // meters
  velocity?: Point2D; // For dynamic obstacles
}

export interface Formation {
  formation_id: string;
  type: "line" | "column" | "wedge" | "circle" | "grid";
  center: Point2D;
  robot_ids: string[];
  scale: number; // Formation size multiplier
}

export interface VisualizationState {
  robots: RobotPose[];
  paths: PlannedPath[];
  obstacles: Obstacle[];
  formations: Formation[];
  world_bounds: {
    min_x: number;
    max_x: number;
    min_y: number;
    max_y: number;
  };
  timestamp: number;
}

// ========== Visualization Config ==========

export interface VisualizationConfig {
  canvas_width: number;
  canvas_height: number;
  meters_per_pixel: number;
  grid_spacing_meters: number;
  show_grid: boolean;
  show_robot_ids: boolean;
  show_velocities: boolean;
  show_paths: boolean;
  show_formations: boolean;
  robot_radius_meters: number;
  colors: {
    background: string;
    grid: string;
    robot_idle: string;
    robot_moving: string;
    robot_charging: string;
    robot_error: string;
    path: string;
    obstacle_static: string;
    obstacle_dynamic: string;
    obstacle_human: string;
    formation: string;
    text: string;
  };
}

export const DEFAULT_VIZ_CONFIG: VisualizationConfig = {
  canvas_width: 800,
  canvas_height: 600,
  meters_per_pixel: 0.05, // 1 pixel = 5cm
  grid_spacing_meters: 1.0, // 1 meter grid
  show_grid: true,
  show_robot_ids: true,
  show_velocities: true,
  show_paths: true,
  show_formations: true,
  robot_radius_meters: 0.3, // 30cm radius
  colors: {
    background: "#0a0a0a",
    grid: "#1a1a1a",
    robot_idle: "#3b82f6", // blue-500
    robot_moving: "#10b981", // green-500
    robot_charging: "#f59e0b", // amber-500
    robot_error: "#ef4444", // red-500
    path: "#8b5cf6", // violet-500
    obstacle_static: "#6b7280", // gray-500
    obstacle_dynamic: "#f97316", // orange-500
    obstacle_human: "#ec4899", // pink-500
    formation: "#14b8a6", // teal-500
    text: "#e5e7eb", // gray-200
  },
};

// ========== Demo Data Generator ==========

export class DemoDataGenerator {
  private robots: RobotPose[] = [];
  private obstacles: Obstacle[] = [];
  private time: number = 0;

  constructor(private num_robots: number = 5) {
    this.initializeRobots();
    this.initializeObstacles();
  }

  private initializeRobots() {
    const robot_ids = ["robot_01", "robot_02", "robot_03", "robot_04", "robot_05"];

    for (let i = 0; i < this.num_robots; i++) {
      this.robots.push({
        robot_id: robot_ids[i] || `robot_${i + 1}`,
        position: {
          x: Math.random() * 20 - 10, // -10 to 10 meters
          y: Math.random() * 20 - 10,
        },
        orientation_rad: Math.random() * 2 * Math.PI,
        velocity: Math.random() * 0.5,
        status: Math.random() > 0.8 ? "idle" : "moving",
        battery_percent: 50 + Math.random() * 50,
      });
    }
  }

  private initializeObstacles() {
    // Static obstacles (walls, furniture)
    for (let i = 0; i < 3; i++) {
      this.obstacles.push({
        id: `static_${i}`,
        type: "static",
        position: {
          x: Math.random() * 20 - 10,
          y: Math.random() * 20 - 10,
        },
        radius: 0.5 + Math.random() * 0.5,
      });
    }

    // Dynamic obstacles (humans, carts)
    for (let i = 0; i < 2; i++) {
      this.obstacles.push({
        id: `human_${i}`,
        type: "human",
        position: {
          x: Math.random() * 20 - 10,
          y: Math.random() * 20 - 10,
        },
        radius: 0.3,
        velocity: {
          x: (Math.random() - 0.5) * 0.2,
          y: (Math.random() - 0.5) * 0.2,
        },
      });
    }
  }

  public update(delta_time_seconds: number): VisualizationState {
    this.time += delta_time_seconds;

    // Update robot positions
    this.robots.forEach((robot) => {
      if (robot.status === "moving") {
        const dx = Math.cos(robot.orientation_rad) * robot.velocity * delta_time_seconds;
        const dy = Math.sin(robot.orientation_rad) * robot.velocity * delta_time_seconds;

        robot.position.x += dx;
        robot.position.y += dy;

        // Wrap around world bounds
        if (robot.position.x > 15) robot.position.x = -15;
        if (robot.position.x < -15) robot.position.x = 15;
        if (robot.position.y > 15) robot.position.y = -15;
        if (robot.position.y < -15) robot.position.y = 15;

        // Occasionally change direction
        if (Math.random() < 0.02) {
          robot.orientation_rad += (Math.random() - 0.5) * Math.PI / 2;
        }

        // Occasionally stop
        if (Math.random() < 0.01) {
          robot.status = "idle";
          robot.velocity = 0;
        }
      } else if (robot.status === "idle") {
        // Occasionally start moving
        if (Math.random() < 0.02) {
          robot.status = "moving";
          robot.velocity = Math.random() * 0.5 + 0.2;
        }
      }

      // Drain battery slowly
      robot.battery_percent = Math.max(0, robot.battery_percent - 0.1 * delta_time_seconds);
    });

    // Update dynamic obstacles
    this.obstacles.forEach((obstacle) => {
      if (obstacle.type === "human" && obstacle.velocity) {
        obstacle.position.x += obstacle.velocity.x * delta_time_seconds;
        obstacle.position.y += obstacle.velocity.y * delta_time_seconds;

        // Bounce off walls
        if (Math.abs(obstacle.position.x) > 15) {
          obstacle.velocity.x *= -1;
        }
        if (Math.abs(obstacle.position.y) > 15) {
          obstacle.velocity.y *= -1;
        }
      }
    });

    // Generate paths for moving robots
    const paths: PlannedPath[] = this.robots
      .filter((r) => r.status === "moving")
      .map((robot) => {
        const segments: PathSegment[] = [];
        let current = { ...robot.position };

        // Generate 3-5 path segments ahead
        const num_segments = 3 + Math.floor(Math.random() * 3);
        for (let i = 0; i < num_segments; i++) {
          const next = {
            x: current.x + Math.cos(robot.orientation_rad + (Math.random() - 0.5) * 0.5) * 2,
            y: current.y + Math.sin(robot.orientation_rad + (Math.random() - 0.5) * 0.5) * 2,
          };

          segments.push({
            start: current,
            end: next,
            cost: Math.hypot(next.x - current.x, next.y - current.y),
          });

          current = next;
        }

        const total_cost = segments.reduce((sum, seg) => sum + seg.cost, 0);

        return {
          robot_id: robot.robot_id,
          segments,
          total_cost,
          eta_seconds: total_cost / (robot.velocity || 0.5),
        };
      });

    // Generate formation (optional, for first 3 robots if they exist)
    const formations: Formation[] = [];
    if (this.robots.length >= 3 && Math.sin(this.time * 0.5) > 0.8) {
      const center_robot = this.robots[0];
      formations.push({
        formation_id: "demo_formation",
        type: "line",
        center: center_robot.position,
        robot_ids: this.robots.slice(0, 3).map((r) => r.robot_id),
        scale: 1.0,
      });
    }

    return {
      robots: this.robots,
      paths,
      obstacles: this.obstacles,
      formations,
      world_bounds: {
        min_x: -20,
        max_x: 20,
        min_y: -20,
        max_y: 20,
      },
      timestamp: Date.now(),
    };
  }

  public getRobots(): RobotPose[] {
    return this.robots;
  }

  public getObstacles(): Obstacle[] {
    return this.obstacles;
  }
}
