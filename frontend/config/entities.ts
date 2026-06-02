

export interface EntityMeta {
    label: string;
    color: string;
    anonymizeLabel: string;
} 

/**
 * Definition of Entities used for identifiying PII and anonymising it
 */
export const ENTITY_CONFIG: Record<string, EntityMeta> = {
  PERSON:        { 
    label: "Person",  
    color: "bg-red-100 text-red-700 border-red-200",
    anonymizeLabel: "[PERSON]"
 },
  EMAIL_ADDRESS: { 
    label: "E-Mail",  
    color: "bg-blue-100 text-blue-700 border-blue-200",
    anonymizeLabel: "[EMAIL]"
 },
  PHONE_NUMBER:  {
    label: "Telefon",
    color: "bg-yellow-100 text-yellow-700 border-yellow-200",
    anonymizeLabel: "[TELEFON]"
 },
  URL: {
    label: "Webseite",
    color: "bg-cyan-100 text-cyan-700 border-cyan-200",
    anonymizeLabel: "[WEBSEITE]"
 },
  LOCATION:      { 
    label: "Ort",     
    color: "bg-green-100 text-green-700 border-green-200",
    anonymizeLabel: "[ORT]"
 },
  IBAN_CODE:     { 
    label: "IBAN",    
    color: "bg-purple-100 text-purple-700 border-purple-200",
    anonymizeLabel: "[IBAN]"
 },
  ORGANIZATION:  { 
    label: "Firma",   
    color: "bg-orange-100 text-orange-700 border-orange-200",
    anonymizeLabel: "[FIRMA]"
 },
  ADDRESS:       {
    label: "Adresse",
    color: "bg-amber-100 text-amber-700 border-amber-200",
    anonymizeLabel: "[ADRESSE]"
 },
  TAX_CODE:             {
    label: "Steuer-ID",
    color: "bg-rose-100 text-rose-700 border-rose-200",
    anonymizeLabel: "[STEUER_ID]"
 },
  BANK_ACCOUNT_NUMBER:  {
    label: "Kontonummer",
    color: "bg-sky-100 text-sky-700 border-sky-200",
    anonymizeLabel: "[KONTO_NR]"
 },
  LICENSE_PLATE_NUMBER: {
    label: "Kfz-Kennzeichen",
    color: "bg-lime-100 text-lime-700 border-lime-200",
    anonymizeLabel: "[KFZ]"
 },
  BIRTHDAY:             {
    label: "Geburtstag",
    color: "bg-teal-100 text-teal-700 border-teal-200",
    anonymizeLabel: "[GEBURTSTAG]"
 },
  ID_CARD_NUMBER:       {
    label: "Ausweis-Nr.",
    color: "bg-violet-100 text-violet-700 border-violet-200",
    anonymizeLabel: "[AUSWEIS_NR]"
 },
};

export const getEntitiyMeta = (type: string): EntityMeta => {
    return (
        ENTITY_CONFIG[type] ?? {
            label: type,
            color: "bg-muted text-foreground border-border",
            anonymizeLabel: `[${type}]`,
        }
    )
}