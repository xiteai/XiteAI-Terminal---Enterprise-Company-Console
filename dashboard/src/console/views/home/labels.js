export const KIND = {
  news: { label: "News", icon: "sparkle" },
  achievement: { label: "Achievement", icon: "cap" },
  funding: { label: "Funding", icon: "activity" },
  event: { label: "Event", icon: "calendar" },
};

export function birthdayLine(b) {
  if (b.days_away === 0) return `Turns ${b.turns} today`;
  if (b.days_away === 1) return `Turns ${b.turns} tomorrow`;
  return `Turns ${b.turns} in ${b.days_away} days`;
}
