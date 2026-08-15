import { getInitial, getAvatarColor } from "@/utils/user";

interface AvatarProps {
  avatarPath?: string | null;
  displayName: string;
  seed: string | number;
  size?: number;
  className?: string;
}

export default function Avatar({
  avatarPath,
  displayName,
  seed,
  size = 32,
  className = "",
}: AvatarProps) {
  const style = { width: size, height: size };

  if (avatarPath) {
    return (
      <img
        src={avatarPath}
        alt={displayName}
        style={style}
        className={`rounded-full object-cover flex-shrink-0 ${className}`}
      />
    );
  }

  return (
    <div
      style={{ ...style, backgroundColor: getAvatarColor(String(seed)) }}
      className={`rounded-full flex items-center justify-center flex-shrink-0 text-white font-medium ${className}`}
      aria-label={displayName}
    >
      <span style={{ fontSize: size * 0.45 }}>{getInitial(displayName)}</span>
    </div>
  );
}
