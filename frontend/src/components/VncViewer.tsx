import React, { useRef, useEffect, useState, useCallback } from 'react';
// @ts-ignore — @novnc/novnc ships plain JS, no type declarations
import RFB from '@novnc/novnc';
import './VncViewer.css';

interface VncViewerProps {
  /** WebSocket URL, e.g. ws://localhost:6080 or derived from window.location */
  wsUrl?: string;
  /** Whether to attempt connection (tie to bot running state) */
  connected?: boolean;
}

const VncViewer: React.FC<VncViewerProps> = ({ wsUrl, connected = true }) => {
  const canvasRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  /** Build the default WebSocket URL from the current page origin */
  const getWsUrl = useCallback((): string => {
    if (wsUrl) return wsUrl;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${window.location.host}/websockify`;
  }, [wsUrl]);

  /** Connect to the VNC server */
  const connect = useCallback(() => {
    if (!canvasRef.current) return;

    // Tear down any existing connection
    if (rfbRef.current) {
      try {
        rfbRef.current.disconnect();
      } catch {
        // ignore
      }
      rfbRef.current = null;
    }

    setStatus('connecting');
    setError(null);

    try {
      const url = getWsUrl();
      const rfb = new RFB(canvasRef.current, url, {
        // no credentials needed
      });

      rfb.scaleViewport = true;
      rfb.resizeSession = false;
      rfb.showDotCursor = true;

      rfb.addEventListener('connect', () => {
        setStatus('connected');
        setError(null);
      });

      rfb.addEventListener('disconnect', (e: CustomEvent) => {
        setStatus('disconnected');
        if (e.detail?.clean === false) {
          setError('Connection lost. The bot may not be running.');
        }
        rfbRef.current = null;
      });

      rfb.addEventListener('securityfailure', (e: CustomEvent) => {
        setError(`Security error: ${e.detail?.reason ?? 'unknown'}`);
      });

      rfbRef.current = rfb;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setStatus('disconnected');
    }
  }, [getWsUrl]);

  /** Disconnect from the VNC server */
  const disconnect = useCallback(() => {
    if (rfbRef.current) {
      try {
        rfbRef.current.disconnect();
      } catch {
        // ignore
      }
      rfbRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  /** Toggle fullscreen mode */
  const toggleFullscreen = useCallback(() => {
    if (!wrapperRef.current) return;

    if (!document.fullscreenElement) {
      wrapperRef.current.requestFullscreen().catch((err) => {
        console.error('Error attempting to enable fullscreen:', err);
      });
    } else {
      document.exitFullscreen();
    }
  }, []);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Auto-connect / disconnect when the `connected` prop changes
  useEffect(() => {
    if (connected) {
      connect();
    } else {
      disconnect();
    }
    return () => {
      disconnect();
    };
  }, [connected, connect, disconnect]);

  return (
    <div className="vnc-viewer-wrapper" ref={wrapperRef}>
      {/* Toolbar */}
      <div className="vnc-toolbar">
        <div className="vnc-status">
          <span className={`vnc-dot vnc-dot-${status}`} />
          <span className="vnc-status-text">
            {status === 'connecting' && 'Connecting…'}
            {status === 'connected' && 'Connected — Chrome live view'}
            {status === 'disconnected' && 'Disconnected'}
          </span>
        </div>
        <div className="vnc-actions">
          {status === 'connected' && (
            <button
              className="btn btn-sm btn-secondary"
              onClick={toggleFullscreen}
              title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? (
                <span>↲ Exit Fullscreen</span>
              ) : (
                <span>⛶ Fullscreen</span>
              )}
            </button>
          )}
          {status === 'disconnected' && (
            <button className="btn btn-sm btn-primary" onClick={connect}>
              Reconnect
            </button>
          )}
          {status === 'connected' && (
            <button className="btn btn-sm btn-secondary" onClick={disconnect}>
              Disconnect
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {error && <div className="vnc-error">{error}</div>}

      {/* Canvas container — noVNC renders inside this div */}
      <div
        ref={canvasRef}
        className={`vnc-canvas ${status !== 'connected' ? 'vnc-canvas-hidden' : ''}`}
      />

      {/* Placeholder when not connected */}
      {status !== 'connected' && (
        <div className="vnc-placeholder">
          <div className="vnc-placeholder-icon">🖥️</div>
          <p>
            {status === 'connecting'
              ? 'Connecting to Chrome browser…'
              : 'Start the bot to view the Chrome browser here.'}
          </p>
        </div>
      )}
    </div>
  );
};

export default VncViewer;
