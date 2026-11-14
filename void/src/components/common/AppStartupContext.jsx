import { createContext, useContext } from "react";

const AppStartupContext = createContext(false);

export const AppStartupProvider = AppStartupContext.Provider;
export const useAppStartup = () => useContext(AppStartupContext);
