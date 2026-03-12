import { getRequestConfig } from "next-intl/server";

export default getRequestConfig(async ({ requestLocale }) => {
    const locale = await requestLocale;
    return {
        locale: locale ?? "es",
        messages: (await import(`../messages/${locale ?? "es"}.json`)).default,
    };
});