"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import { Camera, RefreshCw, Upload, AlertCircle, X, ImageIcon } from "lucide-react";

interface CameraFeedProps {
  onCapture: (base64Image: string) => void;
  isLoading: boolean;
}

export default function CameraFeed({ onCapture, isLoading }: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [facingMode, setFacingMode] = useState<"user" | "environment">("environment");
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Start the camera feed
  const startCamera = async () => {
    setPermissionError(null);
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    try {
      const constraints = {
        video: {
          facingMode: facingMode,
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setCameraActive(true);
    } catch (err: any) {
      console.error("Camera access error:", err);
      setPermissionError(
        "Could not access camera. Please allow camera permissions or upload an image file instead."
      );
      setCameraActive(false);
    }
  };

  // Stop the camera feed
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setCameraActive(false);
  };

  // Start camera on mount and cleanup on unmount
  useEffect(() => {
    startCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [facingMode]);

  // Toggle front/back camera
  const toggleCamera = () => {
    setFacingMode((prev) => (prev === "user" ? "environment" : "user"));
  };

  // Capture frame from live video
  const captureFrame = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");

      if (ctx) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        if (facingMode === "user") {
          ctx.translate(canvas.width, 0);
          ctx.scale(-1, 1);
        }
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        setPreviewImage(dataUrl);
        onCapture(dataUrl);
      }
    }
  };

  // Process an image file (from upload or drag-drop)
  const processFile = useCallback(
    (file: File) => {
      // Validate file type
      const validTypes = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/heic"];
      if (!validTypes.includes(file.type) && !file.name.match(/\.(jpe?g|png|webp|gif|heic)$/i)) {
        alert("Please upload a valid image file (JPEG, PNG, WEBP, GIF, HEIC).");
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === "string") {
          setPreviewImage(reader.result);
          onCapture(reader.result);
        }
      };
      reader.readAsDataURL(file);
    },
    [onCapture]
  );

  // Handle click-to-upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    // Reset input so the same file can be re-selected
    e.target.value = "";
  };

  // Drag-and-drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const clearPreview = () => setPreviewImage(null);

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
