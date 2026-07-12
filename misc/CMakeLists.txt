add_executable(check_rels check_rels.cpp)
target_link_libraries(check_rels utils_with_io)
install(TARGETS check_rels RUNTIME DESTINATION ${LIBSUFFIX}/misc)

if (HAVE_GMPECM)
add_executable(descent_init_Fp descent_init_Fp.cpp smooth_detect.cpp)
target_link_libraries(descent_init_Fp utils ecm)
install(TARGETS descent_init_Fp RUNTIME DESTINATION ${LIBSUFFIX}/misc)
endif()

if(HAVE_GMPECM)
    add_executable(factor factor.cpp)
    target_link_libraries(factor utils ecm)
endif()

add_executable(cl_structure_from_group_order cl_structure_from_group_order.cpp)
target_link_libraries(cl_structure_from_group_order utils)

include(CMakeLists-nodist.txt OPTIONAL)
