(function () {
    'use strict';
    // Original Next implementation; no Classic/Vendetta runtime dependency.
    function splitText(text, limit) {
        const parts = [];
        let remaining = text;
        while (remaining.length > limit) {
            let end = limit;
            const newline = remaining.lastIndexOf('\n', limit - 1);
            const space = remaining.lastIndexOf(' ', limit - 1);
            if (newline >= limit / 2) end = newline + 1;
            else if (space >= limit / 2) end = space + 1;
            // Keep UTF-16 surrogate pairs intact at a hard boundary.
            const c = remaining.charCodeAt(end - 1);
            if (c >= 0xd800 && c <= 0xdbff) end--;
            parts.push(remaining.slice(0, end));
            remaining = remaining.slice(end);
        }
        if (remaining) parts.push(remaining);
        return parts;
    }
    const definition = {
        start(api) {
            let active = true;
            const queues = new Map();
            const { getModules } = revenge.modules.finders;
            const { withProps } = revenge.modules.finders.filters;
            const { Stores } = revenge.discord.flux;
            const { instead } = revenge.patcher;
            api.cleanup(() => { active = false; });
            api.cleanup(getModules(withProps('getMaxMessageLength'), limits => {
                if (!active) return;
                api.cleanup(instead(limits, 'getMaxMessageLength', () => 40000));
            }));
            api.cleanup(getModules(withProps('sendMessage', 'editMessage', '_sendMessage'), messages => {
                if (!active) return;
                api.cleanup(instead(messages, 'sendMessage', function (args, original) {
                    const [channelId, message] = args;
                    const content = message?.content;
                    const limit = Stores.UserStore?.getCurrentUser()?.premiumType === 2 ? 4000 : 2000;
                    if (typeof content !== 'string' || content.length <= limit) return original.apply(this, args);
                    const parts = splitText(content, limit);
                    if (parts.length > 20) throw new Error('Split Messages: maximum 20 parts; shorten the message.');
                    const receiver = this;
                    const previous = queues.get(channelId) || Promise.resolve();
                    const task = previous.catch(() => {}).then(async () => {
                        if (!active) throw new Error('Split Messages stopped before sending.');
                        const firstArgs = args.slice();
                        firstArgs[1] = { ...message, content: parts[0] };
                        const first = await original.apply(receiver, firstArgs);
                        for (const part of parts.slice(1)) {
                            const slowmode = Stores.ChannelStore?.getChannel(channelId)?.rateLimitPerUser || 0;
                            await new Promise(resolve => setTimeout(resolve, Math.max(1200, slowmode * 1000 + 250)));
                            if (!active) throw new Error('Split Messages stopped; remaining parts were not sent.');
                            await messages._sendMessage(channelId, {
                                content: part,
                                tts: false,
                                invalidEmojis: message.invalidEmojis,
                                validNonShortcutEmojis: message.validNonShortcutEmojis,
                            }, {});
                        }
                        return first;
                    });
                    queues.set(channelId, task);
                    task.then(() => { if (queues.get(channelId) === task) queues.delete(channelId); }, error => {
                        if (queues.get(channelId) === task) queues.delete(channelId);
                        api.plugin.reportError('Split Messages stopped sending: ' + String(error));
                    });
                    return task;
                }));
            }));
        },
    };
    return { default: plugin(definition), splitText };
})()
