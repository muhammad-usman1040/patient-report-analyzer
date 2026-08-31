import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ur from "./locales/ur.json";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ur: { translation: ur },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export const changeLanguage = (code) => i18n.changeLanguage(code);
export default i18n;
