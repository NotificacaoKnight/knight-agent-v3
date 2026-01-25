import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2 } from 'lucide-react';

interface AudioPlayerProps {
  audioUrl: string;
  transcription?: string;
  initialDuration?: number;
  isProcessingTranscription?: boolean;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, transcription, initialDuration, isProcessingTranscription }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMetadataLoaded, setIsMetadataLoaded] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Utility function to validate and normalize duration values
  const validateDuration = useCallback((value: number): number => {
    if (!value || !isFinite(value) || isNaN(value) || value <= 0) {
      return 0;
    }
    return Math.max(0, value);
  }, []);

  // Utility function to validate and normalize time values
  const validateTime = useCallback((value: number): number => {
    if (!isFinite(value) || isNaN(value) || value < 0) {
      return 0;
    }
    return Math.max(0, value);
  }, []);

  // Set duration with priority logic: prefer initialDuration (from backend) over audio.duration
  const updateDuration = useCallback((audioDuration?: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    // Priority 1: Use initialDuration (from backend) if available - mais confiável
    if (initialDuration && initialDuration > 0) {
      const validatedDuration = validateDuration(initialDuration);
      if (validatedDuration > 0) {
        setDuration(validatedDuration);
        return;
      }
    }

    // Priority 2: Use actual audio duration if available and valid
    if (audioDuration !== undefined) {
      const validatedDuration = validateDuration(audioDuration);
      if (validatedDuration > 0) {
        setDuration(validatedDuration);
        return;
      }
    }

    // Priority 3: Use audio.duration if metadata is loaded (apenas como último recurso)
    if (isMetadataLoaded && audio.duration) {
      const validatedDuration = validateDuration(audio.duration);
      if (validatedDuration > 0) {
        setDuration(validatedDuration);
        return;
      }
    }
  }, [initialDuration, isMetadataLoaded, validateDuration]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    // Reset state when audio URL changes
    setIsMetadataLoaded(false);
    setCurrentTime(0);
    setIsPlaying(false);

    // Set initial duration from prop if available - esta é a duração mais confiável
    if (initialDuration && initialDuration > 0) {
      const validatedDuration = validateDuration(initialDuration);
      setDuration(validatedDuration);
      console.log('🎵 AudioPlayer: Setting initial duration from prop:', validatedDuration);
    }

    const handleLoadedMetadata = () => {
      setIsMetadataLoaded(true);
      // Não atualizar duração aqui para não sobrescrever initialDuration
      // updateDuration será chamado apenas se initialDuration não estiver disponível
      if (!initialDuration || initialDuration <= 0) {
        console.log('🎵 AudioPlayer: No initialDuration, using audio.duration:', audio.duration);
        updateDuration(audio.duration);
      } else {
        console.log('🎵 AudioPlayer: Keeping initialDuration:', initialDuration, 'instead of audio.duration:', audio.duration);
      }
    };

    const handleTimeUpdate = () => {
      const validatedTime = validateTime(audio.currentTime);
      setCurrentTime(validatedTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const handleError = (e: Event) => {
      console.error('Audio loading error:', e);
      setIsMetadataLoaded(false);
      setIsPlaying(false);
    };

    // Use only loadedmetadata for duration to avoid race conditions
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [audioUrl, initialDuration, updateDuration, validateTime, validateDuration]);

  const togglePlayback = async () => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      if (isPlaying) {
        audio.pause();
        setIsPlaying(false);
      } else {
        await audio.play();
        setIsPlaying(true);
      }
    } catch (error) {
      console.error('Playback error:', error);
      setIsPlaying(false);
    }
  };

  const formatTime = (time: number) => {
    const validatedTime = validateTime(time);
    if (validatedTime === 0) {
      return '0:00';
    }
    const minutes = Math.floor(validatedTime / 60);
    const seconds = Math.floor(validatedTime % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || duration <= 0) return;

    const progressBar = e.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const clickX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const percentage = clickX / rect.width;
    const newTime = percentage * duration;
    
    const validatedTime = validateTime(newTime);
    audio.currentTime = Math.min(validatedTime, duration);
    setCurrentTime(validatedTime);
  };

  // Calculate progress percentage with proper edge case handling
  const getProgressPercentage = (): number => {
    if (duration <= 0 || currentTime < 0) {
      return 0;
    }
    const percentage = (currentTime / duration) * 100;
    return Math.min(Math.max(percentage, 0), 100);
  };

  return (
    <div className="max-w-xs">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      <div className="flex items-center space-x-3">
        <button
          onClick={togglePlayback}
          className="flex-shrink-0 w-8 h-8 bg-primary-foreground/10 hover:bg-primary-foreground/20 text-primary-foreground rounded-full flex items-center justify-center transition-colors"
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 ml-0.5" />
          )}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <Volume2 className="h-3 w-3 text-primary-foreground/70" />
            <span className="text-xs text-primary-foreground/70">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          <div
            className="w-full h-1 bg-primary-foreground/20 rounded-full cursor-pointer"
            onClick={handleProgressClick}
          >
            <div
              className="h-full bg-primary-foreground/60 rounded-full transition-all duration-150"
              style={{
                width: `${getProgressPercentage()}%`
              }}
            />
          </div>
        </div>
      </div>

      {(transcription || isProcessingTranscription) && (
        <div className="mt-3 pt-3 border-t border-primary-foreground/20">
          {transcription ? (
            <p className="text-sm text-primary-foreground/80 italic">
              "{transcription}"
            </p>
          ) : isProcessingTranscription ? (
            <p className="text-sm text-primary-foreground/60 italic">
              "Carregando..."
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
};