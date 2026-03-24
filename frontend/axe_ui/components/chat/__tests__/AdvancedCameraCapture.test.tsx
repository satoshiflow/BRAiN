import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AdvancedCameraCapture } from "@/components/chat/AdvancedCameraCapture";

const createMockTrack = () => ({
  stop: jest.fn(),
});

const createMockStream = () => {
  const track = createMockTrack();
  return {
    getTracks: jest.fn(() => [track]),
    track,
  };
};

describe("AdvancedCameraCapture", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        getUserMedia: jest.fn(),
      },
    });
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <AdvancedCameraCapture open={false} onClose={jest.fn()} onCapture={jest.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("starts camera stream when opened", async () => {
    const stream = createMockStream();
    const getUserMedia = jest
      .spyOn(navigator.mediaDevices, "getUserMedia")
      .mockResolvedValue(stream as unknown as MediaStream);

    render(<AdvancedCameraCapture open={true} onClose={jest.fn()} onCapture={jest.fn()} />);

    await waitFor(() => {
      expect(getUserMedia).toHaveBeenCalled();
    });
    expect(screen.getByRole("button", { name: "Capture" })).toBeInTheDocument();
  });

  it("shows fallback button when permission is denied", async () => {
    const deniedError = new Error("Permission denied");
    deniedError.name = "NotAllowedError";

    jest.spyOn(navigator.mediaDevices, "getUserMedia").mockRejectedValue(deniedError);

    const onClose = jest.fn();
    const onFallbackToFilePicker = jest.fn();

    render(
      <AdvancedCameraCapture
        open={true}
        onClose={onClose}
        onCapture={jest.fn()}
        onFallbackToFilePicker={onFallbackToFilePicker}
      />
    );

    const fallbackButton = await screen.findByRole("button", {
      name: "Select image instead",
    });
    fireEvent.click(fallbackButton);

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onFallbackToFilePicker).toHaveBeenCalledTimes(1);
  });

  it("stops media tracks when unmounted", async () => {
    const stream = createMockStream();
    jest
      .spyOn(navigator.mediaDevices, "getUserMedia")
      .mockResolvedValue(stream as unknown as MediaStream);

    const { unmount } = render(
      <AdvancedCameraCapture open={true} onClose={jest.fn()} onCapture={jest.fn()} />
    );

    await waitFor(() => {
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
    });

    unmount();

    expect(stream.getTracks).toHaveBeenCalled();
    expect(stream.track.stop).toHaveBeenCalled();
  });
});
