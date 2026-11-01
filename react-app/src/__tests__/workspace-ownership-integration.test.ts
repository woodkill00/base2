import { expect, test } from 'vitest';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = (name: string) => readFileSync(`e2e/${name}`, 'utf8');
test('the whole setup and both async workspace bodies enter ownership before any body work', () => {
  const text = source('workspace/workspace-release.spec.ts');
  const ast = ts.createSourceFile('workspace.ts', text, ts.ScriptTarget.Latest, true);
  let bodies = 0;
  for (const statement of ast.statements) {
    if (!ts.isExpressionStatement(statement) || !ts.isCallExpression(statement.expression)) continue;
    const call = statement.expression;
    if (!['test', 'test.beforeEach'].includes(call.expression.getText(ast))) continue;
    const callback = call.arguments.at(-1)!;
    if (!ts.isArrowFunction(callback) || !callback.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword)) continue;
    expect(ts.isBlock(callback.body)).toBe(true);
    const statements = (callback.body as ts.Block).statements;
    const first = statements[0];
    const selected = call.arguments[0]?.getText(ast).includes('selected record editing');
    if (selected) {
      expect(ts.isExpressionStatement(first) && ts.isCallExpression(first.expression) && first.expression.expression.getText(ast)).toBe('test.skip');
      expect(statements).toHaveLength(2);
    } else expect(statements).toHaveLength(1);
    expect(statements[selected ? 1 : 0].getText(ast)).toMatch(/^return ownedWorkspaceBody\(\s*page,\s*testInfo,/);
    bodies++;
  }
  expect(bodies).toBe(3);
});

test('workspace and nested capture awaits cannot introduce unguarded body continuations', () => {
  const failures: string[] = [];
  for (const name of ['workspace/workspace-release.spec.ts', 'scroll-target.ts', 'continuous-scroll.ts']) {
    const ast = ts.createSourceFile(name, source(name), ts.ScriptTarget.Latest, true);
    const visit = (node: ts.Node) => {
      if (ts.isAwaitExpression(node)) {
        let browserOrRoute = false, hook = false;
        for (let parent = node.parent; parent; parent = parent.parent) {
          if ((ts.isArrowFunction(parent) || ts.isFunctionExpression(parent)) && ts.isCallExpression(parent.parent)) {
            const call = parent.parent;
            const expression = call.expression;
            if (ts.isPropertyAccessExpression(expression) && ['evaluate', 'evaluateAll', 'evaluateHandle', 'route'].includes(expression.name.text)) browserOrRoute = true;
            if (expression.getText(ast) === 'ownedWorkspaceHook') hook = true;
          }
        }
        const guarded = ts.isCallExpression(node.expression) && ['ownershipStep', 'ownershipCleanup', 'ownedWorkspaceHook'].includes(node.expression.expression.getText(ast));
        if (!browserOrRoute && !hook && !guarded) failures.push(`${name}:${ast.getLineAndCharacterOfPosition(node.pos).line+1}`);
      }
      ts.forEachChild(node, visit);
    };
    visit(ast);
  }
  expect(failures).toEqual([]);
});
