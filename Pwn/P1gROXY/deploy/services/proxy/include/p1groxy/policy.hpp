#pragma once

#include "p1groxy/http.hpp"

#include <string>

namespace p1groxy {

void normalize_request_for_upstream(HttpRequest& request,
                                    const std::string& upstream_host,
                                    const std::string& upstream_port,
                                    const std::string& client_addr);
bool normalize_response_body_for_client(HttpResponse& response,
                                        const std::string& upstream_host,
                                        const std::string& upstream_port);
void normalize_response_for_client(HttpResponse& response);

}  // namespace p1groxy
