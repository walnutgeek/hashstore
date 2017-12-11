import Cake from './Cake';
import WebPath,{AliasPath} from './WebPath';

test('AliasPath', () => {
    let longer_cake = new Cake('1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV');
    expect(new AliasPath([longer_cake, "a", "b.txt"]).toString())
        .toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/b.txt")
});

test('WebPath', () => {

    let ap = new WebPath(undefined);
    expect(ap.root).toBeTruthy();
    expect(ap.settings).toBeFalsy();
    expect(ap.aliasPath).toBeFalsy();

    ap = new WebPath("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/b.txt");
    expect(ap.root).toBeFalsy();
    expect(ap.settings).toBeFalsy();
    expect(ap.aliasPath).toBeTruthy();

    expect(ap.slash).toBe(false);
    expect(ap.name).toBe("b.txt");
    expect(ap.ext()).toBe("txt");
    expect(ap.aliasPath.toString())
        .toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/b.txt");
    expect(ap.toString()).toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/b.txt");

    ap = new WebPath("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/");
    expect(ap.root).toBeFalsy();
    expect(ap.settings).toBeFalsy();
    expect(ap.aliasPath).toBeTruthy();

    expect(ap.slash).toBe(true);
    expect(ap.name).toBe("a");
    expect(ap.ext()).toBe("/");
    expect(ap.aliasPath.toString())
        .toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/");
    expect(ap.toString()).toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a/");

    ap = new WebPath("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a");
    expect(ap.root).toBeFalsy();
    expect(ap.settings).toBeFalsy();
    expect(ap.aliasPath).toBeTruthy();

    expect(ap.slash).toBe(false);
    expect(ap.name).toBe("a");
    expect(ap.ext()).toBe(null);
    expect(ap.aliasPath.isCakeBased()).toBe(true);
    expect(ap.aliasPath.toString())
        .toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a");
    expect(ap.toString()).toBe("_/1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV/a");

    ap = new WebPath("~/acl");
    expect(ap.root).toBeFalsy();
    expect(ap.settings).toBeTruthy();
    expect(ap.aliasPath).toBeFalsy();

    expect(ap.settings).toEqual(['acl']);

    ap = new WebPath("~");
    expect(ap.root).toBeFalsy();
    expect(ap.settings).toBeTruthy();
    expect(ap.aliasPath).toBeFalsy();

    expect(ap.settings).toEqual([]);

    ap = new WebPath("abc/xyz");
    expect(ap.root).toBeFalsy();
    expect(ap.settings).toBeFalsy();
    expect(ap.aliasPath).toBeTruthy();

    expect(ap.aliasPath.isCakeBased()).toBe(false);
    expect(ap.aliasPath.path).toEqual(['abc','xyz']);
    expect(ap.aliasPath.subpath(1).toString()).toEqual('abc/');
    expect(ap.aliasPath.toString()).toEqual('abc/xyz');

    ap = new WebPath("");
    expect(ap.root).toBeTruthy();
    expect(ap.settings).toBeFalsy();
    expect(ap.aliasPath).toBeFalsy();
});
