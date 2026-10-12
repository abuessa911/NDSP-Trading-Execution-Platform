export type PropRow = [name: string, type: string, def: string, required: boolean, en: string, ar: string];
type P2 = [en: string, ar: string];
export type FamilyDoc = {
  id: string; purpose: P2; when: P2; whenNot: P2; composition: P2; props: PropRow[]; copy: P2; a11y: P2; kbd: P2; example: string;
};
