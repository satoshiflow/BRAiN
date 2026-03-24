import { render, screen } from "@testing-library/react";

function TestComponent() {
  return <div>AXE UI test harness</div>;
}

describe("test setup", () => {
  it("renders a basic component", () => {
    render(<TestComponent />);
    expect(screen.getByText("AXE UI test harness")).toBeInTheDocument();
  });
});
