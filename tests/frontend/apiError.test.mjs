import test from 'node:test';
import assert from 'node:assert/strict';
import {
  extractResponseErrorMessage,
  formatApiErrorDetail,
} from '../../src/utils/apiError.ts';

test('TC-SRC-15.1: formatApiErrorDetail formats Pydantic 422 array detail without [object Object]', () => {
  const validationDetail = [
    {
      type: 'greater_than_equal',
      loc: ['body', 'limit'],
      msg: 'Input should be greater than or equal to 1',
      input: -1,
    },
    {
      type: 'greater_than_equal',
      loc: ['body', 'offset'],
      msg: 'Input should be greater than or equal to 0',
      input: -5,
    },
  ];

  const formatted = formatApiErrorDetail(validationDetail);
  assert.equal(
    formatted,
    'body.limit: Input should be greater than or equal to 1; body.offset: Input should be greater than or equal to 0',
  );
  assert.equal(formatted?.includes('[object Object]'), false);
});

test('TC-SRC-15.2: formatApiErrorDetail handles string, numeric loc, missing loc, empty array, and plain objects', () => {
  assert.equal(formatApiErrorDetail('Photo not found'), 'Photo not found');
  assert.equal(formatApiErrorDetail('   '), null);
  assert.equal(formatApiErrorDetail([]), null);
  assert.equal(formatApiErrorDetail([{}]), null);
  assert.equal(
    formatApiErrorDetail([{ loc: ['body', 'tags', 0], msg: 'String should have at least 1 character' }]),
    'body.tags.0: String should have at least 1 character',
  );
  assert.equal(
    formatApiErrorDetail([{ msg: 'Invalid payload' }, 'Extra constraint failed']),
    'Invalid payload; Extra constraint failed',
  );
  assert.equal(formatApiErrorDetail({ message: 'Database unavailable' }), 'Database unavailable');
  assert.equal(formatApiErrorDetail({}), null);
});

test('TC-SRC-15.3: extractResponseErrorMessage extracts 422 detail and falls back cleanly on empty or invalid JSON', async () => {
  const validationResponse = new Response(
    JSON.stringify({
      detail: [
        {
          loc: ['body', 'limit'],
          msg: 'Input should be less than or equal to 500',
        },
      ],
    }),
    { status: 422, statusText: 'Unprocessable Entity' },
  );
  assert.equal(
    await extractResponseErrorMessage(validationResponse, 'Failed to search photos'),
    'body.limit: Input should be less than or equal to 500',
  );

  const emptyDetailResponse = new Response(JSON.stringify({ detail: [] }), {
    status: 422,
    statusText: 'Unprocessable Entity',
  });
  assert.equal(
    await extractResponseErrorMessage(emptyDetailResponse, 'Failed to search photos'),
    'Unprocessable Entity',
  );

  const nonJsonResponse = new Response('Bad Gateway', {
    status: 502,
    statusText: '',
  });
  assert.equal(
    await extractResponseErrorMessage(nonJsonResponse, 'Failed to search photos'),
    'Failed to search photos',
  );
});
