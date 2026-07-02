# Implementation References

P1gROXY is not a fork of these projects, but its module boundaries and HTTP terminology follow common proxy implementations and current HTTP specifications.

- NGINX source: https://github.com/nginx/nginx
- NGINX chunked filter: https://github.com/nginx/nginx/blob/master/src/http/modules/ngx_http_chunked_filter_module.c
- NGINX gunzip filter: https://github.com/nginx/nginx/blob/master/src/http/modules/ngx_http_gunzip_filter_module.c
- HAProxy source: https://github.com/haproxy/haproxy
- HAProxy compression documentation: https://www.haproxy.com/documentation/haproxy-configuration-tutorials/performance/compression/
- Envoy source: https://github.com/envoyproxy/envoy
- Envoy decompressor filter: https://github.com/envoyproxy/envoy/tree/main/source/extensions/filters/http/decompressor
- RFC 9112 HTTP/1.1: https://www.rfc-editor.org/rfc/rfc9112.html
