# Known Issues

先送りした既知の問題。直したら Open から Resolved へ移す。

## Open

### KI-1: JSON 配列の要素を型で検証していない

- 出典: M-2（PR「Lua の JSON を文法どおりのパーサとエンコーダに置き換える」）の Codex review。既存の問題として除外
- 内容: `ParamType.JSON_ARRAY` の引数（`catalog.addKeywords` の `keywords` など）は、配列であることだけを確かめ、要素の型を見ていない。`["a", null]` を渡すと、Lua 側の `ipairs` に `MessageProtocol.null` が届き、`catalog:createKeyword` が SDK の型エラーで止まる。途中まで追加したキーワードは残る（部分更新）
- 以前の挙動: 旧パーサは `null` を文字列 `"null"` として渡していたので、`null` という名前のキーワードができていた
- 直し方の案: `validation.py` で JSON 配列の要素の型を引数ごとに宣言して検証する。Lua 側の各ハンドラでも要素の型を確かめる
- 重大度: P2（CLI / MCP の呼び出し側が明らかに不正な値を渡したときだけ起きる）

## Resolved

（なし）
