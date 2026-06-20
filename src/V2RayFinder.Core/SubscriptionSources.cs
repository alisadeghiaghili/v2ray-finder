namespace V2RayFinder.Core;

/// <summary>
/// Curated list of public V2Ray subscription sources.
/// Equivalent to the Python source registry in v2ray-finder.
/// </summary>
public static class SubscriptionSources
{
    public static readonly IReadOnlyList<string> Urls = new[]
    {
        // barry-far
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/All_Configs_Sub.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vless.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/trojan.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/ss.txt",

        // Epodonios
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",

        // ebrasha
        "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/subs/all.txt",
        "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/subs/vmess.txt",
        "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/subs/vless.txt",

        // mahdibland
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/Eternity",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",

        // tbbatbb
        "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",

        // yebekhe
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/base64/mix",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",

        // freefq
        "https://raw.githubusercontent.com/freefq/free/master/v2",

        // peasoft
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",

        // ermaozi
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",

        // mfuu
        "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",

        // soroushmirzaei
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/splitted/mixed",
    };
}
