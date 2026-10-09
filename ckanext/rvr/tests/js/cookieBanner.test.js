// Run with: node --test ckanext/rvr/tests/js/cookieBanner.test.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'assets/js/cookieBanner.js'), 'utf8');

function createBanner(stored = null, options = {}) {
    let definition;
    let checked = false;
    const classes = new Set(['cookie-banner']);
    const handlers = new Map();
    const published = [];
    const timers = [];
    const context = {
        ckan: {module(name, factory) { definition = factory(); }},
        localStorage: {
            getItem() {
                if (options.blockRead) throw new Error('SecurityError');
                return stored;
            },
            setItem(key, value) {
                if (options.blockWrite) throw new Error('QuotaExceededError');
                stored = value;
            }
        },
        setTimeout(callback) { timers.push(callback); }
    };
    if (options.missingStorage) delete context.localStorage;
    vm.runInNewContext(source, context);
    const instance = Object.assign({}, definition, {
        sandbox: {publish(name, enabled) { published.push([name, enabled]); }},
        el: {
            removeClass(value) {
                value.split(' ').forEach(name => classes.delete(name));
                return this;
            },
            addClass(value) {
                value.split(' ').forEach(name => classes.add(name));
                return this;
            },
            on(event, selector, callback) { handlers.set(event + ' ' + selector, callback); },
            find() {
                return {
                    prop(name, value) { checked = value; },
                    is() { return checked; }
                };
            }
        }
    });
    instance.initialize();
    return {
        instance, classes, handlers, published,
        getStored() { return stored; },
        getChecked() { return checked; },
        getTimerCount() { return timers.length; },
        changeAnalytics(value) {
            checked = value;
            handlers.get('change .cookie-banner__analytics-toggle')({});
        },
        flushTimers() { timers.splice(0).forEach(callback => callback()); },
        click(selector) {
            handlers.get('click ' + selector)({preventDefault() {}});
        }
    };
}

test('first visit shows the banner with analytics disabled and handlers registered', () => {
    const banner = createBanner();
    assert.ok(banner.classes.has('cookie-banner--visible'));
    assert.deepEqual(banner.published, [['analytics_enabled', false]]);
    assert.equal(banner.handlers.size, 6);
});

test('changing analytics persists each choice without closing the banner', () => {
    const banner = createBanner();
    for (const analytics of [true, false]) {
        banner.changeAnalytics(analytics);
        assert.equal(JSON.parse(banner.getStored()).analytics, analytics);
        assert.deepEqual(banner.published.at(-1), ['analytics_enabled', analytics]);
        assert.ok(banner.classes.has('cookie-banner--visible'));
        assert.ok(!banner.classes.has('cookie-banner--hidden'));
        assert.ok(!banner.classes.has('cookie-banner--minimized'));
        assert.equal(banner.getTimerCount(), 0);
    }
});

for (const selector of ['.cookie-banner__accept-all', '.cookie-banner__reject', '.cookie-banner__close']) {
    test(selector + ' immediately restores the notice and allows reopening', () => {
        const banner = createBanner();
        banner.click(selector);
        assert.ok(banner.classes.has('cookie-banner--minimized'));
        assert.ok(!banner.classes.has('cookie-banner--visible'));
        assert.ok(!banner.classes.has('cookie-banner--hidden'));
        assert.equal(banner.getTimerCount(), 0);
        banner.click('.cookie-banner__minimized-content');
        banner.flushTimers();
        assert.ok(banner.classes.has('cookie-banner--visible'));
        assert.ok(!banner.classes.has('cookie-banner--minimized'));
    });
}

for (const analytics of [true, false]) {
    test('saved analytics=' + analytics + ' retains a working settings control', () => {
        const banner = createBanner(JSON.stringify({necessary: true, analytics}));
        assert.ok(banner.classes.has('cookie-banner--minimized'));
        assert.deepEqual(banner.published, [['analytics_enabled', analytics]]);
        banner.click('.cookie-banner__minimized-content');
        assert.ok(banner.classes.has('cookie-banner--visible'));
        assert.equal(banner.getChecked(), analytics);
    });
}

for (const stored of ['invalid json', 'null', '{}', '[]',
    '{"necessary":true,"analytics":"false"}', '{"analytics":true}']) {
    test('invalid stored consent is ignored: ' + stored, () => {
        const banner = createBanner(stored);
        assert.ok(banner.classes.has('cookie-banner--visible'));
        assert.deepEqual(banner.published, [['analytics_enabled', false]]);
        banner.click('.cookie-banner__reject');
        assert.equal(JSON.parse(banner.getStored()).analytics, false);
    });
}

for (const options of [
    {blockRead: true, blockWrite: true},
    {blockWrite: true},
    {missingStorage: true}
]) {
    test('unavailable persistence keeps consent controls functional: ' + JSON.stringify(options), () => {
        const banner = createBanner(null, options);
        banner.click('.cookie-banner__accept-all');
        banner.flushTimers();
        assert.ok(banner.classes.has('cookie-banner--minimized'));
        assert.deepEqual(banner.published.at(-1), ['analytics_enabled', true]);
        banner.click('.cookie-banner__minimized-content');
        assert.equal(banner.getChecked(), true);
        banner.click('.cookie-banner__reject');
        assert.deepEqual(banner.published.at(-1), ['analytics_enabled', false]);
    });
}

test('a failed write overrides previously saved consent in memory', () => {
    const banner = createBanner(JSON.stringify({necessary: true, analytics: true}), {blockWrite: true});
    banner.click('.cookie-banner__minimized-content');
    banner.click('.cookie-banner__reject');
    banner.flushTimers();
    banner.click('.cookie-banner__minimized-content');
    assert.equal(banner.getChecked(), false);
    assert.deepEqual(banner.published.at(-1), ['analytics_enabled', false]);
});

test('accept persists consent and restores the minimized control on a new page', () => {
    const banner = createBanner();
    banner.click('.cookie-banner__accept-all');
    banner.flushTimers();
    const saved = JSON.parse(banner.getStored());
    assert.equal(saved.necessary, true);
    assert.equal(saved.analytics, true);
    assert.ok(saved.timestamp);
    const nextPage = createBanner(banner.getStored());
    assert.ok(nextPage.classes.has('cookie-banner--minimized'));
});

test('the settings control is a native button with a visible focus style', () => {
    const template = fs.readFileSync(path.join(root, 'templates/base.html'), 'utf8');
    const css = fs.readFileSync(path.join(root, 'assets/css/rvr.css'), 'utf8');
    assert.match(template, /<button type="button" class="cookie-banner__minimized-content">/);
    assert.match(css, /\.cookie-banner__minimized-content:focus\s*\{[^}]*outline: 2px solid #fff;/);
});
