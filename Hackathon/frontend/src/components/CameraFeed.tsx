"use client";

import React, {
  useRef,
  useState,
  useEffect,
  useCallback,
} from "react";

import {
  Camera,
  RefreshCw,
  Upload,
  AlertCircle,
  X,
  ImageIcon,
} from "lucide-react";

interface CameraFeedProps {
  onCapture: (base64Image: string) => void;
  isLoading: boolean;
}

export default function CameraFeed({
  onCapture,
  isLoading,
}: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [facingMode, setFacingMode] = useState<
    "user" | "environment"
  >("environment");

  const [permissionError, setPermissionError] = useState<string | null>(
    null
  );

  const [cameraActive, setCameraActive] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // ============================================================
  // STOP CAMERA
  // ============================================================

  const stopCamera = useCallback(() => {
    setStream((currentStream) => {
      if (currentStream) {
        currentStream.getTracks().forEach((track) => {
          track.stop();
        });
      }

      return null;
    });

    setCameraActive(false);

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // ============================================================
  // START CAMERA
  // ============================================================

  const startCamera = useCallback(async () => {
    setPermissionError(null);

    // Stop previous stream
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia
    ) {
      setPermissionError(
        "Camera is not supported by this browser. Please upload an image instead."
      );

      setCameraActive(false);
      return;
    }

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: {
            ideal: facingMode,
          },
          width: {
            ideal: 1280,
          },
          height: {
            ideal: 720,
          },
        },
        audio: false,
      };

      const mediaStream =
        await navigator.mediaDevices.getUserMedia(constraints);

      setStream(mediaStream);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;

        // Make sure the video starts playing.
        try {
          await videoRef.current.play();
        } catch (playError) {
          console.warn(
            "Video autoplay warning:",
            playError
          );
        }
      }

      setCameraActive(true);
    } catch (error) {
      console.error("Camera access error:", error);

      setCameraActive(false);

      setPermissionError(
        "Could not access the camera. Please allow camera permission or upload an image instead."
      );
    }
  }, [facingMode, stream]);

  // ============================================================
  // CAMERA LIFECYCLE
  // ============================================================

  useEffect(() => {
    let mounted = true;

    const initializeCamera = async () => {
      if (!mounted) return;

      await startCamera();
    };

    initializeCamera();

    return () => {
      mounted = false;

      if (stream) {
        stream.getTracks().forEach((track) => {
          track.stop();
        });
      }

      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [facingMode]);

  // ============================================================
  // TOGGLE FRONT / BACK CAMERA
  // ============================================================

  const toggleCamera = () => {
    setFacingMode((previous) =>
      previous === "user" ? "environment" : "user"
    );
  };

  // ============================================================
  // CAPTURE CAMERA FRAME
  // ============================================================

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      alert("Camera is not ready yet. Please try again.");
      return;
    }

    if (
      !video.videoWidth ||
      !video.videoHeight
    ) {
      alert(
        "Camera image is not ready yet. Please wait a moment and try again."
      );
      return;
    }

    const context = canvas.getContext("2d");

    if (!context) {
      alert("Could not process the camera image.");
      return;
    }

    // Use the actual camera resolution.
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Reset canvas transformation.
    context.setTransform(1, 0, 0, 1, 0, 0);

    // Mirror front camera preview/capture.
    if (facingMode === "user") {
      context.translate(canvas.width, 0);
      context.scale(-1, 1);
    }

    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height
    );

    // Always create a JPEG data URI.
    // This is compatible with the FastAPI backend.
    const dataUrl = canvas.toDataURL(
      "image/jpeg",
      0.85
    );

    if (
      !dataUrl ||
      !dataUrl.startsWith("data:image/jpeg;base64,")
    ) {
      alert("Could not create a valid image.");
      return;
    }

    console.log(
      "Camera image captured successfully:",
      dataUrl.substring(0, 40) + "..."
    );

    setPreviewImage(dataUrl);

    // Send proper Base64 data URI to page.tsx.
    onCapture(dataUrl);
  };

  // ============================================================
  // PROCESS UPLOADED IMAGE
  // ============================================================

  const processFile = useCallback(
    (file: File) => {
      if (!file) {
        return;
      }

      // Supported formats
      const validMimeTypes = [
        "image/jpeg",
        "image/png",
        "image/webp",
      ];

      const validExtensions =
        /\.(jpe?g|png|webp)$/i;

      const isValidMimeType =
        validMimeTypes.includes(file.type);

      const isValidExtension =
        validExtensions.test(file.name);

      if (
        !isValidMimeType &&
        !isValidExtension
      ) {
        alert(
          "Please upload a valid JPG, PNG, or WEBP image."
        );
        return;
      }

      // Prevent extremely large files.
      const MAX_FILE_SIZE =
        10 * 1024 * 1024; // 10 MB

      if (file.size > MAX_FILE_SIZE) {
        alert(
          "Image is too large. Please upload an image smaller than 10 MB."
        );
        return;
      }

      const reader = new FileReader();

      reader.onload = () => {
        if (
          typeof reader.result !== "string"
        ) {
          alert(
            "Could not read the selected image."
          );
          return;
        }

        const dataUrl = reader.result;

        // Make absolutely sure the result is an image data URI.
        if (
          !dataUrl.startsWith("data:image/")
        ) {
          alert(
            "The selected file could not be converted into a valid image."
          );
          return;
        }

        console.log(
          "Image uploaded successfully:",
          dataUrl.substring(0, 40) + "..."
        );

        setPreviewImage(dataUrl);

        // Send Base64 data URI to page.tsx.
        onCapture(dataUrl);
      };

      reader.onerror = () => {
        console.error(
          "FileReader error:",
          reader.error
        );

        alert(
          "Could not read the image file. Please try another image."
        );
      };

      reader.readAsDataURL(file);
    },
    [onCapture]
  );

  // ============================================================
  // FILE INPUT
  // ============================================================

  const handleFileUpload = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (file) {
      processFile(file);
    }

    // Allow selecting the same file again.
    event.target.value = "";
  };

  // ============================================================
  // OPEN FILE PICKER
  // ============================================================

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  // ============================================================
  // DRAG OVER
  // ============================================================

  const handleDragOver = (
    event: React.DragEvent<HTMLDivElement>
  ) => {
    event.preventDefault();
    event.stopPropagation();

    if (!isLoading) {
      setIsDragging(true);
    }
  };

  // ============================================================
  // DRAG LEAVE
  // ============================================================

  const handleDragLeave = (
    event: React.DragEvent<HTMLDivElement>
  ) => {
    event.preventDefault();
    event.stopPropagation();

    setIsDragging(false);
  };

  // ============================================================
  // DROP IMAGE
  // ============================================================

  const handleDrop = (
    event: React.DragEvent<HTMLDivElement>
  ) => {
    event.preventDefault();
    event.stopPropagation();

    setIsDragging(false);

    if (isLoading) {
      return;
    }

    const file = event.dataTransfer.files?.[0];

    if (file) {
      processFile(file);
    }
  };

  // ============================================================
  // CLEAR PREVIEW
  // ============================================================

  const clearPreview = () => {
    setPreviewImage(null);

    // Restart camera if it was stopped.
    if (!cameraActive) {
      startCamera();
    }
  };

  return (
    <div className="flex flex-col items-center bg-gray-50 rounded-2xl border border-gray-200 overflow-hidden shadow-inner w-full relative">
      {/* Video / Preview Container */}
      <div
        className={`relative aspect-[4/3] w-full bg-black flex items-center justify-center overflow-hidden transition-all ${
          isDragging ? "ring-4 ring-rose-400 ring-offset-2" : ""
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Image Preview Mode */}
        {previewImage ? (
          <div className="relative w-full h-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewImage}
              alt="Uploaded monument"
              className="w-full h-full object-contain bg-black"
            />
            {/* Clear preview button */}
            {!isLoading && (
              <button
                onClick={clearPreview}
                className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white p-1.5 rounded-full transition-colors z-10"
                title="Clear image and use camera"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ) : cameraActive && !permissionError ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover ${facingMode === "user" ? "scale-x-[-1]" : ""}`}
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-6 text-center text-gray-400">
            <Camera className="w-12 h-12 mb-3 text-gray-600 animate-pulse" />
            <p className="text-sm font-medium px-4">
              {permissionError || "Initializing camera..."}
            </p>
          </div>
        )}

        {/* Drag-and-drop overlay hint */}
        {isDragging && (
          <div className="absolute inset-0 bg-rose-500/20 flex flex-col items-center justify-center z-20 backdrop-blur-sm">
            <ImageIcon className="w-14 h-14 text-rose-500 mb-2 animate-bounce" />
            <p className="text-rose-700 font-bold text-sm">Drop image here!</p>
          </div>
        )}

        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center text-white z-30">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-rose-500 border-t-transparent mb-3" />
            <p className="font-semibold tracking-wide">Identifying Monument...</p>
            <p className="text-xs text-gray-300 mt-1">Gemini Vision AI analyzing image</p>
          </div>
        )}
      </div>

      {/* Control Panel */}
      <div className="w-full bg-white p-4 flex flex-col space-y-3 border-t border-gray-100">
        {/* Upload + Switch Camera row */}
        <div className="flex justify-between items-center w-full gap-3">
          {/* File Upload Button */}
          <label
            className="flex items-center justify-center p-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl cursor-pointer transition-colors flex-1 text-sm font-semibold select-none border border-gray-200"
            title="Upload or drag-and-drop an image"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload / Drop Image
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,image/heic,.heic,.heif"
              className="hidden"
              onChange={handleFileUpload}
              disabled={isLoading}
            />
          </label>

          {/* Switch Camera (only when camera active and no preview) */}
          {cameraActive && !previewImage && (
            <button
              onClick={toggleCamera}
              disabled={isLoading}
              className="flex items-center justify-center p-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-colors border border-gray-200"
              title="Switch Front / Back Camera"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Drag hint text */}
        <p className="text-center text-[10px] text-gray-400 font-medium -mt-1">
          You can also <strong>drag & drop</strong> any monument image onto the viewfinder above
        </p>

        {/* Capture / Identify button */}
        {previewImage ? (
          /* If preview exists, offer to re-identify */
          <button
            onClick={() => onCapture(previewImage)}
            disabled={isLoading}
            className="w-full py-3.5 bg-gradient-to-r from-rose-500 to-pink-600 hover:from-rose-600 hover:to-pink-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all transform active:scale-[0.98] flex items-center justify-center gap-2"
          >
            <Camera className="w-5 h-5" />
            Identify This Monument
          </button>
        ) : (
          cameraActive && (
            <button
              onClick={captureFrame}
              disabled={isLoading}
              className="w-full py-3.5 bg-gradient-to-r from-rose-500 to-pink-600 hover:from-rose-600 hover:to-pink-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all transform active:scale-[0.98] flex items-center justify-center gap-2"
            >
              <Camera className="w-5 h-5" />
              Identify Monument
            </button>
          )
        )}
      </div>

      {/* Hidden Canvas for frame extraction */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
